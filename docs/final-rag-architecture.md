# Final RAG Architecture Decision

Date: 2026-06-15

## Decision

Prep Academy uses one unified retrieval system for all RAG sources:

- Medical RAG
- Tutor RAG
- Obsidian RAG

All active retrieval flows through `backend/routes/rag.py` and `backend/services/retrieval_orchestrator.py`.

## Production Vector Store

Qdrant is the only active production vector database.

Chroma is deprecated and may remain read-only during migration for backward compatibility. New ingestion must not create active Chroma retrieval paths.

## Embeddings

All sources must share one embedding space. Do not mix embedding models in the same active Qdrant collection.

## Retrieval Contract

The retrieval orchestrator owns:

- source routing
- score normalization
- hybrid scoring
- reranking
- context assembly metadata
- latency reporting per retrieval stage

No endpoint or service should query a vector database directly for active retrieval. It must call the orchestrator.

## Ingestion Contract

Ingestion must be job-based:

- API calls enqueue work and return a job id.
- background workers perform chunking, embedding, and Qdrant upserts.
- job status tracks progress, failures, attempts, and final result.
- watchers are disabled by default in production unless a distributed lock is added.

## Migration Rule

Backward compatibility is allowed only while migrating existing endpoints. Compatibility wrappers must delegate to the unified schema and must not become parallel retrieval pipelines.
