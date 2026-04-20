"""Tests for :mod:`pd_agent.rag.chunker`."""

from __future__ import annotations

import pytest

from pd_agent.rag.chunker import (
    DEFAULT_CHUNK_SIZE_CHARS,
    DEFAULT_OVERLAP_CHARS,
    chunk_document,
)
from pd_agent.rag.types import Document


def _mk(content: str, source: str = "/tmp/doc.md", title: str | None = None) -> Document:
    return Document(source=source, title=title, content=content)


class TestBasicBehavior:
    def test_empty_content_returns_no_chunks(self):
        assert chunk_document(_mk("")) == []

    def test_whitespace_only_content_returns_no_chunks(self):
        assert chunk_document(_mk("   \n\n  \n")) == []

    def test_short_no_heading_is_single_chunk(self):
        chunks = chunk_document(_mk("Just one sentence."))
        assert len(chunks) == 1
        assert "Just one sentence." in chunks[0].text

    def test_chunk_ids_are_sequential_and_padded(self):
        content = "\n\n".join(f"## Section {i}\n\nBody {i}." for i in range(3))
        chunks = chunk_document(_mk(content, source="/tmp/x.md"))
        ids = [c.id for c in chunks]
        assert ids == ["/tmp/x.md#0000", "/tmp/x.md#0001", "/tmp/x.md#0002"]

    def test_chunk_source_and_title_propagated(self):
        chunks = chunk_document(
            _mk("# Top\n\nBody.", source="/tmp/a.md", title="Top"),
        )
        assert all(c.source == "/tmp/a.md" for c in chunks)
        assert all(c.title == "Top" for c in chunks)


class TestHeadingAwareness:
    def test_each_heading_becomes_its_own_chunk(self):
        content = (
            "# Root\n\nIntro paragraph.\n\n"
            "## Section A\n\nContent A.\n\n"
            "## Section B\n\nContent B.\n\n"
            "### Section B.1\n\nContent B.1."
        )
        chunks = chunk_document(_mk(content, title="Root"))
        assert len(chunks) == 4
        headings = [c.metadata.get("heading") for c in chunks]
        assert headings == [
            "Root",
            "Root / Section A",
            "Root / Section B",
            "Root / Section B / Section B.1",
        ]

    def test_heading_prefix_appears_in_chunk_text(self):
        chunks = chunk_document(_mk("## Installation\n\nRun it."))
        assert "# Installation" in chunks[0].text
        assert "Run it." in chunks[0].text

    def test_no_headings_still_chunks(self):
        chunks = chunk_document(_mk("Plain paragraph one.\n\nPlain paragraph two."))
        assert len(chunks) == 1
        assert "paragraph one" in chunks[0].text
        assert "paragraph two" in chunks[0].text

    def test_empty_heading_only_section_is_dropped(self):
        content = "# Has Content\n\nBody.\n\n## Empty\n"
        chunks = chunk_document(_mk(content))
        headings = [c.metadata.get("heading") for c in chunks]
        assert "Has Content / Empty" not in headings


class TestSizeBasedSplitting:
    def test_long_section_splits_into_multiple_chunks(self):
        paragraph = "A" * 600 + "."
        content = "## Big\n\n" + "\n\n".join([paragraph] * 5)
        chunks = chunk_document(_mk(content), chunk_size_chars=1000, overlap_chars=100)
        assert len(chunks) >= 2
        for c in chunks:
            assert c.metadata["heading"] == "Big"

    def test_all_chunks_respect_size_ceiling_approximately(self):
        paragraph = ("one two three four five six seven eight nine ten. " * 30).strip()
        content = "## Long\n\n" + paragraph
        size = 500
        chunks = chunk_document(_mk(content), chunk_size_chars=size, overlap_chars=50)
        assert len(chunks) >= 2
        # Allow some slack for heading prefix + overlap prepend.
        for c in chunks:
            assert len(c.text) <= size + 300

    def test_paragraph_larger_than_chunk_is_hard_split(self):
        huge = "X" * 1500
        content = "## Huge\n\n" + huge
        chunks = chunk_document(_mk(content), chunk_size_chars=500, overlap_chars=50)
        assert len(chunks) >= 2

    def test_default_sizes_are_as_documented(self):
        assert DEFAULT_CHUNK_SIZE_CHARS == 2000
        assert DEFAULT_OVERLAP_CHARS == 256


class TestValidation:
    def test_zero_chunk_size_raises(self):
        with pytest.raises(ValueError):
            chunk_document(_mk("x"), chunk_size_chars=0)

    def test_negative_overlap_raises(self):
        with pytest.raises(ValueError):
            chunk_document(_mk("x"), overlap_chars=-1)

    def test_overlap_not_smaller_than_chunk_size_raises(self):
        with pytest.raises(ValueError):
            chunk_document(_mk("x"), chunk_size_chars=100, overlap_chars=100)


class TestDeterminism:
    def test_same_input_yields_same_chunks(self):
        content = "# A\n\nalpha\n\n## B\n\nbeta gamma delta\n\n## C\n\nepsilon zeta eta"
        doc = _mk(content, source="/tmp/det.md", title="A")
        chunks1 = chunk_document(doc)
        chunks2 = chunk_document(doc)
        assert [c.id for c in chunks1] == [c.id for c in chunks2]
        assert [c.text for c in chunks1] == [c.text for c in chunks2]
