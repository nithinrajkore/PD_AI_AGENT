"""Document loaders for the RAG ingestion pipeline.

Loaders are I/O adapters: they read a source file off disk, normalize it to
plain text (markdown-flavored where possible), and return a
:class:`~pd_agent.rag.types.Document`. The chunker downstream never sees a
raw file -- only ``Document`` objects -- which keeps the chunking logic
format-agnostic.

Supported sources in v0.3.0:

* Markdown / plain text files (``.md``, ``.markdown``, ``.txt``)
* PDF files (``.pdf``) via :mod:`pymupdf4llm`

Web pages and other sources may be added in later releases.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from pd_agent.rag.types import Document

__all__ = [
    "MARKDOWN_EXTENSIONS",
    "PDF_EXTENSIONS",
    "load_directory",
    "load_markdown_file",
    "load_pdf_file",
]

MARKDOWN_EXTENSIONS: tuple[str, ...] = (".md", ".markdown", ".txt")
PDF_EXTENSIONS: tuple[str, ...] = (".pdf",)

_H1_PATTERN = re.compile(r"^\s*#\s+(.+?)\s*$", re.MULTILINE)


def _extract_title(content: str) -> str | None:
    """Pull the first level-1 markdown heading out of ``content``.

    Returns ``None`` if no ``# Heading`` line exists in the first 20 lines.
    Restricting to the top of the document avoids picking up a heading
    that merely appears in an example block deep in the file.
    """

    head = "\n".join(content.splitlines()[:20])
    match = _H1_PATTERN.search(head)
    return match.group(1).strip() if match else None


def load_markdown_file(path: Path) -> Document:
    """Load a markdown / plain-text file into a :class:`Document`.

    The file's UTF-8 contents become ``Document.content`` verbatim. The
    first ``# Heading`` line (if any) becomes ``Document.title``.
    ``metadata`` records the source file's extension under
    ``doc_type`` so downstream consumers can treat PDFs and markdown
    differently if they need to.
    """

    resolved = path.resolve()
    content = resolved.read_text(encoding="utf-8")
    return Document(
        source=str(resolved),
        title=_extract_title(content),
        content=content,
        metadata={
            "doc_type": "markdown",
            "file_ext": resolved.suffix.lower(),
        },
    )


def load_pdf_file(path: Path) -> Document:
    """Load a PDF file into a :class:`Document` via ``pymupdf4llm``.

    ``pymupdf4llm.to_markdown`` converts the PDF into markdown-flavored
    text that preserves headings, lists, and basic table structure --
    much better for downstream chunking than raw plain-text extraction.
    """

    import pymupdf4llm

    resolved = path.resolve()
    content = pymupdf4llm.to_markdown(str(resolved))
    return Document(
        source=str(resolved),
        title=_extract_title(content),
        content=content,
        metadata={
            "doc_type": "pdf",
            "file_ext": resolved.suffix.lower(),
        },
    )


def _iter_matching_files(
    root: Path,
    extensions: Iterable[str],
) -> Iterable[Path]:
    """Yield files under ``root`` whose suffix (lower-cased) is in ``extensions``."""

    ext_set = {e.lower() for e in extensions}
    for candidate in sorted(root.rglob("*")):
        if candidate.is_file() and candidate.suffix.lower() in ext_set:
            yield candidate


def load_directory(
    path: Path,
    *,
    markdown_extensions: Iterable[str] = MARKDOWN_EXTENSIONS,
    pdf_extensions: Iterable[str] = PDF_EXTENSIONS,
) -> list[Document]:
    """Recursively load every markdown + PDF file under ``path``.

    Unreadable files are silently skipped; corrupt PDFs are common in
    real corpora and we do not want one bad file to abort a bulk
    ingestion run. The returned documents are sorted by source path for
    deterministic output.
    """

    if not path.is_dir():
        raise NotADirectoryError(f"Corpus root is not a directory: {path}")

    documents: list[Document] = []

    for md_path in _iter_matching_files(path, markdown_extensions):
        try:
            documents.append(load_markdown_file(md_path))
        except (OSError, UnicodeDecodeError):
            continue

    for pdf_path in _iter_matching_files(path, pdf_extensions):
        try:
            documents.append(load_pdf_file(pdf_path))
        except Exception:
            continue

    return documents
