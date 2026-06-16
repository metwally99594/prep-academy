# Unified RAG

Prep Academy uses one active retrieval stack for Medical RAG, Tutor RAG, Metsu, and Obsidian notes.

## Active Stack

| Component | Production choice |
|---|---|
| Entry point | `backend/routes/rag.py` |
| Orchestration | `backend/services/retrieval_orchestrator.py` |
| Vector store | Qdrant |
| Embeddings | shared provider from `backend/embeddings.py` |
| Hybrid scoring | vector score plus lexical BM25-like score |
| Reranking | unified cross-encoder when available |
| Legacy store | Chroma is deprecated/read-only compatibility only |

## Retrieval Contract

Active retrieval must call the orchestrator:

```python
from services.retrieval_orchestrator import RetrievalRequest, retrieve
```

Do not query Chroma, Qdrant, or `vector_store.search_chapters()` directly from endpoints or feature services. Compatibility wrappers may remain inside `vector_store.py`, but they must delegate to the unified Qdrant schema.

## Source Types

Unified results include source metadata so the caller can assemble context without knowing the storage backend:

- `source_type`
- `source`
- `title`
- `chunk_title`
- `document_id`
- `note_title`
- `vault_path`
- `tags`
- `score`
- `retrieval_score`
- stage latency under `orchestrator.stage_latency_ms`

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/rag/status` | Public | RAG readiness and vector store status |
| POST | `/api/rag/query` | User | Unified cited answer |
| POST | `/api/rag/ingest-text` | Admin | Queue text ingestion |
| POST | `/api/rag/ingest-pdf` | Admin | Queue PDF ingestion |
| GET | `/api/rag/sources` | User | List indexed sources |
| DELETE | `/api/rag/source/{source_name}` | Admin | Delete source chunks |
| POST | `/api/rag/obsidian/sync` | Admin | Queue Obsidian incremental sync |
| GET | `/api/rag/obsidian/status` | Admin | Obsidian indexing status |
| POST | `/api/rag/obsidian/reindex` | Admin | Queue full Obsidian reindex |

## Environment

```env
ENABLE_ADVANCED_FEATURES=true
QDRANT_URL=
QDRANT_API_KEY=
OPENROUTER_API_KEY=
OBSIDIAN_VAULT_PATH=
OBSIDIAN_AUTO_SYNC=true
OBSIDIAN_WATCH_CHANGES=false
```

Keep `OBSIDIAN_WATCH_CHANGES=false` in production unless distributed locking and filesystem availability have been verified.

## Verification

```powershell
python -m py_compile backend\routes\rag.py backend\services\retrieval_orchestrator.py backend\vector_store.py
pytest backend\tests\test_unified_rag_boundaries.py
```

Production smoke:

```text
GET https://prep-academy.onrender.com/api/rag/status
```

Expected production indicators:

- `ready=true`
- `active_vector_store=qdrant`
- `legacy_chroma_document_count=0`
