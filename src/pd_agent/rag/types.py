"""Core data models for the RAG pipeline.

These types are deliberately minimal. A :class:`Document` represents one
source input before chunking (one markdown file, one PDF, one web page).
A :class:`Chunk` represents a piece of a document after chunking -- the
unit that gets embedded, indexed, retrieved, re-ranked, and cited in
answers.

Vector embeddings and BM25 term statistics live in their respective
stores, not on these models, so the models stay small and cheap to pass
around.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["Chunk", "Document"]


class Document(BaseModel):
    """A source document before chunking.

    One instance represents one input to the ingestion pipeline -- e.g.
    a single markdown file from the OpenLane 2 docs tree, or a single
    web page whose article body was extracted.
    """

    model_config = ConfigDict(frozen=True)

    source: str = Field(
        description=(
            "Stable identifier for the document origin (absolute path, "
            "canonical URL, etc.). Used for de-duplication during "
            "ingestion and for citation links in answers."
        ),
    )
    title: str | None = Field(
        default=None,
        description="Human-readable title, if known.",
    )
    content: str = Field(
        description="Raw text content of the document, post-extraction.",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Free-form provenance metadata (e.g. doc type, section, "
            "source tool). Values are strings for compatibility with "
            "Chroma's metadata requirements."
        ),
    )


class Chunk(BaseModel):
    """A chunk of a document after chunking.

    The chunk is the unit of retrieval: it is what gets embedded, stored
    in the vector index, scored by BM25, re-ranked by the cross-encoder,
    and ultimately cited in the generated answer.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        description=(
            "Stable identifier for this chunk, unique within the corpus. "
            "Typical format: '{document-source-slug}#{chunk-index}'."
        ),
    )
    text: str = Field(
        description="The chunk's text content, ready to embed.",
    )
    source: str = Field(
        description=(
            "Identifier of the parent Document this chunk came from. "
            "Used to build citations in answers."
        ),
    )
    title: str | None = Field(
        default=None,
        description="Parent document's title, for citation display.",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Chunk-level metadata (section heading, chunk index, etc.). "
            "Stored verbatim in the vector store for filtered retrieval."
        ),
    )
