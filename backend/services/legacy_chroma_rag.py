"""Deprecated Chroma RAG helpers.

The final RAG architecture uses Qdrant through
services.retrieval_orchestrator as the single retrieval path.

This module exists as a migration marker for old Chroma-backed code still
inside routes/rag.py and routes/dicom.py. Do not add new Chroma retrieval here;
move remaining legacy ingestion/status/backup logic behind this module during
the migration.
"""

DEPRECATED_VECTOR_STORE = "chroma"
REPLACEMENT_MODULE = "services.retrieval_orchestrator"
