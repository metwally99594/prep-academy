# Obsidian RAG Integration

Prep Academy can index an Obsidian vault into the same Qdrant collection used by the AI Tutor document RAG pipeline.

## Configuration

Backend environment variables:

```env
OBSIDIAN_VAULT_PATH=/absolute/path/to/obsidian/vault
OBSIDIAN_AUTO_SYNC=true
OBSIDIAN_WATCH_CHANGES=false
OBSIDIAN_WATCH_INTERVAL_SECONDS=60
OBSIDIAN_CHUNK_WORDS=350
OBSIDIAN_CHUNK_OVERLAP=40
```

Existing RAG/Qdrant variables are reused:

```env
QDRANT_URL=
QDRANT_API_KEY=
OPENROUTER_API_KEY=
```

If `QDRANT_URL` and `QDRANT_API_KEY` are absent, the app falls back to local Qdrant storage at `./.qdrant_data`.

## What Is Indexed

Every Markdown note outside `.obsidian/` is scanned. For each note the ingestion service extracts:

- title from frontmatter, first `# H1`, or filename
- folder and vault-relative path
- frontmatter metadata
- Markdown headings
- tags from frontmatter and inline `#tags`
- backlinks from `[[Wiki links]]`
- note body content

Chunks preserve:

- note title
- vault path
- heading hierarchy
- tags
- source note path

## Incremental Updates

File hashes are stored in MongoDB collection `obsidian_rag_files`.

During sync:

- unchanged notes are skipped
- new notes are embedded and upserted
- modified notes delete old vectors then upsert fresh chunks
- removed notes delete corresponding vectors

Vector payloads are stored in the existing Qdrant collection `tutor_chapters` with:

```json
{
  "document_type": "obsidian_note",
  "note_title": "...",
  "vault_path": "...",
  "tags": [],
  "backlinks": [],
  "text": "..."
}
```

## API

All management endpoints require admin auth.

```http
POST /api/rag/obsidian/sync
GET  /api/rag/obsidian/status
POST /api/rag/obsidian/reindex
```

Search endpoint requires normal auth:

```http
GET /api/rag/obsidian/search?q=diabetes&limit=5
```

Search results return:

```json
{
  "note_title": "Diabetes Mellitus",
  "vault_path": "Endocrinology/Diabetes.md",
  "chunk_text": "...",
  "relevance_score": 0.82
}
```

## Unified Retrieval

The AI Tutor, Medical RAG, Metsu, and Obsidian search paths use `services.retrieval_orchestrator` as the active retrieval layer.

Obsidian notes are indexed into the same Qdrant vector collection and are included in unified search results with source metadata (`source_type`, `note_title`, `vault_path`, tags, and scores). Legacy Chroma code remains deprecated/read-only during migration and must not be used for new ingestion.

## Admin UI

Admin → RAG Knowledge includes an Obsidian Vault panel:

- Sync Obsidian Vault
- Reindex Vault
- indexed notes count
- indexed chunks count
- last sync timestamp
- watcher/config status

## Benchmark

Create a JSON/JSONL/CSV file with:

```json
[
  {
    "query": "diagnostic criteria diabetes",
    "expected_path": "Endocrinology/Diabetes.md"
  }
]
```

Run:

```bash
python backend/evaluation/obsidian_rag_benchmark.py \
  --cases data/obsidian_benchmark.json \
  --base-url https://prep-academy.onrender.com \
  --out artifacts/obsidian_rag_benchmark_report.json
```

Metrics:

- Retrieval Recall@5
- Retrieval Recall@10
- MRR
- average latency
- p95 latency

## Operational Notes

On Render, `OBSIDIAN_VAULT_PATH` must point to a path actually available to the backend container. If the vault is not mounted or copied into the deployment, sync will report `configured=false`.

For production, keep `OBSIDIAN_WATCH_CHANGES=false` by default. Prefer manual sync/reindex from the admin panel unless the vault files are reliably available on the backend filesystem and the distributed lock behavior has been verified.
