"""Tests for :mod:`pd_agent.rag.types` core data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pd_agent.rag import Chunk, Document


class TestDocument:
    def test_construct_with_required_fields(self):
        doc = Document(source="/path/to/a.md", content="hello world")
        assert doc.source == "/path/to/a.md"
        assert doc.content == "hello world"
        assert doc.title is None
        assert doc.metadata == {}

    def test_construct_with_all_fields(self):
        doc = Document(
            source="https://example.com/page",
            title="Example Page",
            content="body text",
            metadata={"section": "intro", "doc_type": "web"},
        )
        assert doc.title == "Example Page"
        assert doc.metadata == {"section": "intro", "doc_type": "web"}

    def test_source_required(self):
        with pytest.raises(ValidationError):
            Document(content="no source")  # type: ignore[call-arg]

    def test_content_required(self):
        with pytest.raises(ValidationError):
            Document(source="/a.md")  # type: ignore[call-arg]

    def test_is_frozen(self):
        doc = Document(source="/a.md", content="x")
        with pytest.raises(ValidationError):
            doc.content = "mutated"  # type: ignore[misc]


class TestChunk:
    def test_construct_with_required_fields(self):
        chunk = Chunk(id="a#0", text="hello", source="/a.md")
        assert chunk.id == "a#0"
        assert chunk.text == "hello"
        assert chunk.source == "/a.md"
        assert chunk.title is None
        assert chunk.metadata == {}

    def test_construct_with_all_fields(self):
        chunk = Chunk(
            id="openlane2_intro#3",
            text="OpenLane 2 is a flow...",
            source="docs/openlane2/intro.md",
            title="Introduction",
            metadata={"heading": "Overview", "chunk_index": "3"},
        )
        assert chunk.title == "Introduction"
        assert chunk.metadata["heading"] == "Overview"

    def test_id_required(self):
        with pytest.raises(ValidationError):
            Chunk(text="x", source="y")  # type: ignore[call-arg]

    def test_text_required(self):
        with pytest.raises(ValidationError):
            Chunk(id="x", source="y")  # type: ignore[call-arg]

    def test_source_required(self):
        with pytest.raises(ValidationError):
            Chunk(id="x", text="y")  # type: ignore[call-arg]

    def test_is_frozen(self):
        chunk = Chunk(id="a#0", text="hello", source="/a.md")
        with pytest.raises(ValidationError):
            chunk.text = "mutated"  # type: ignore[misc]

    def test_chunks_with_same_fields_are_equal(self):
        c1 = Chunk(id="a#0", text="hi", source="/a.md")
        c2 = Chunk(id="a#0", text="hi", source="/a.md")
        assert c1 == c2

    def test_chunks_with_different_ids_are_not_equal(self):
        c1 = Chunk(id="a#0", text="hi", source="/a.md")
        c2 = Chunk(id="a#1", text="hi", source="/a.md")
        assert c1 != c2
