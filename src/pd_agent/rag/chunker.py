"""Markdown-aware chunker for the RAG ingestion pipeline.

Takes a :class:`~pd_agent.rag.types.Document` and produces a list of
:class:`~pd_agent.rag.types.Chunk` objects sized for embedding and
retrieval. The chunker respects markdown heading boundaries so that each
chunk tends to cover a single semantic topic. The heading path is
preserved in chunk metadata so citations can name the section the
content came from.

The defaults (``chunk_size_chars=2000``, ``overlap_chars=256``) correspond
to roughly 500 tokens with 64 token overlap, which is standard for
general-purpose retrieval on English technical docs. Tuning knobs are
available per call; we do not expose them in :class:`PDAgentSettings`
until we have eval data to inform good values.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pd_agent.rag.types import Chunk, Document

__all__ = ["DEFAULT_CHUNK_SIZE_CHARS", "DEFAULT_OVERLAP_CHARS", "chunk_document"]

DEFAULT_CHUNK_SIZE_CHARS = 2000
DEFAULT_OVERLAP_CHARS = 256

_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_SENTENCE_BREAK_PATTERN = re.compile(r"(?<=[.!?])\s+")


@dataclass
class _Section:
    """One heading-bounded section of a document."""

    heading_path: list[str] = field(default_factory=list)
    text: str = ""


def _parse_sections(content: str) -> list[_Section]:
    """Split markdown content into sections at heading boundaries.

    Each section carries the stack of headings it lives under (the
    "heading path"), so a chunk inside ``## Installation`` → ``### macOS``
    knows both of those labels and can cite them.
    """

    sections: list[_Section] = [_Section()]
    heading_stack: list[tuple[int, str]] = []  # (level, text)

    for line in content.splitlines():
        match = _HEADING_PATTERN.match(line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            # Pop any headings at the same or deeper level so we correctly
            # represent sibling and shallower headings.
            heading_stack = [(lv, t) for (lv, t) in heading_stack if lv < level]
            heading_stack.append((level, title))
            sections.append(
                _Section(
                    heading_path=[t for (_, t) in heading_stack],
                    text="",
                )
            )
        else:
            sections[-1].text += line + "\n"

    # Strip sections whose text is empty or whitespace-only; they
    # contribute nothing retrievable on their own.
    return [s for s in sections if s.text.strip()]


def _hard_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Fallback splitter when a single paragraph exceeds ``chunk_size``.

    Prefers to break at sentence boundaries within the last 25% of the
    target window. Falls back to a hard character cut if no sentence
    break is available.
    """

    if len(text) <= chunk_size:
        return [text]

    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            window_start = max(start + int(chunk_size * 0.75), start + 1)
            window = text[window_start:end]
            break_match = None
            for m in _SENTENCE_BREAK_PATTERN.finditer(window):
                break_match = m
            if break_match is not None:
                end = window_start + break_match.end()
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [p for p in pieces if p]


def _pack_paragraphs(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Greedy-pack paragraphs into chunks that stay under ``chunk_size``.

    Paragraphs are separated by blank lines. When a single paragraph is
    bigger than ``chunk_size`` we fall back to :func:`_hard_split`.
    Overlap is applied between consecutive chunks by prepending the
    tail of the previous chunk to the start of the next one.
    """

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    buffer = ""

    def _flush() -> None:
        nonlocal buffer
        if buffer.strip():
            chunks.append(buffer.strip())
        buffer = ""

    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            _flush()
            chunks.extend(_hard_split(paragraph, chunk_size, overlap))
            continue

        if buffer and len(buffer) + 2 + len(paragraph) > chunk_size:
            _flush()

        buffer = f"{buffer}\n\n{paragraph}" if buffer else paragraph

    _flush()

    if overlap <= 0 or len(chunks) < 2:
        return chunks

    overlapped: list[str] = [chunks[0]]
    for i in range(1, len(chunks)):
        tail = chunks[i - 1][-overlap:]
        overlapped.append(f"{tail}\n\n{chunks[i]}")
    return overlapped


def _section_to_chunks(
    section: _Section,
    chunk_size: int,
    overlap: int,
) -> list[tuple[str, list[str]]]:
    """Split one section's text into (chunk_text, heading_path) tuples."""

    heading_prefix = ""
    if section.heading_path:
        heading_prefix = "# " + " / ".join(section.heading_path) + "\n\n"
    body = section.text.strip()
    if not body:
        return []

    if len(heading_prefix) + len(body) <= chunk_size:
        return [(f"{heading_prefix}{body}", section.heading_path)]

    body_chunks = _pack_paragraphs(body, chunk_size - len(heading_prefix), overlap)
    return [(f"{heading_prefix}{c}", section.heading_path) for c in body_chunks]


def chunk_document(
    doc: Document,
    *,
    chunk_size_chars: int = DEFAULT_CHUNK_SIZE_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[Chunk]:
    """Split a :class:`Document` into retrieval-ready :class:`Chunk` objects.

    Sections defined by markdown headings (``#``, ``##``, ``###`` ...) are
    preferred chunk boundaries. Large sections are further broken at
    paragraph and sentence boundaries with a configurable character
    overlap. Chunk ids are stable for the same input and have the form
    ``"{doc.source}#{index:04d}"``.
    """

    if chunk_size_chars <= 0:
        raise ValueError("chunk_size_chars must be positive")
    if overlap_chars < 0:
        raise ValueError("overlap_chars must be non-negative")
    if overlap_chars >= chunk_size_chars:
        raise ValueError("overlap_chars must be smaller than chunk_size_chars")

    sections = _parse_sections(doc.content)
    chunks: list[Chunk] = []
    idx = 0
    for section in sections:
        for chunk_text, heading_path in _section_to_chunks(
            section, chunk_size_chars, overlap_chars
        ):
            metadata = dict(doc.metadata)
            metadata["chunk_index"] = f"{idx:04d}"
            if heading_path:
                metadata["heading"] = " / ".join(heading_path)
            chunks.append(
                Chunk(
                    id=f"{doc.source}#{idx:04d}",
                    text=chunk_text,
                    source=doc.source,
                    title=doc.title,
                    metadata=metadata,
                )
            )
            idx += 1
    return chunks
