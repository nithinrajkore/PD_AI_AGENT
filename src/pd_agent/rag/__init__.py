"""RAG (Retrieval-Augmented Generation) pipeline for pd-agent.

This package owns document ingestion, chunking, indexing, retrieval, and
re-ranking. The shared data models (`Document`, `Chunk`) live in
:mod:`pd_agent.rag.types` and are re-exported here for convenience.
"""

from pd_agent.rag.types import Chunk, Document

__all__ = ["Chunk", "Document"]
