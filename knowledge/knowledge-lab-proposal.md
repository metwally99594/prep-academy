# Knowledge Lab — Technical Design Proposal

> Lightweight admin-only wiki browser inside Prep Academy.
> No AI, no embeddings, no vector DB, no RAG.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│  React (CRA + CRACO)   │   /knowledge-lab       │
│                         │                        │
│  ┌──────────┐ ┌──────────────────────┐          │
│  │ Sidebar  │ │ Main Content Area    │          │
│  │ (pages)  │ │ (rendered markdown)  │          │
│  │ search   │ │ related pages        │          │
│  │ filter   │ │ source refs          │          │
│  └────┬─────┘ └──────────┬───────────┘          │
│       │                  │                       │
│       └────────┬─────────┘                       │
│                │ HTTP (Bearer token)             │
└────────────────┼─────────────────────────────────┘
                 │
┌────────────────┼─────────────────────────────────┐
│           Backend (FastAPI)                      │
│                 │                                │
│  ┌─────────────┴────────────┐                   │
│  │  Knowledge Lab Router    │                   │
│  │  (routes/knowledge_lab)  │                   │
│  │                         │                   │
│  │  • list_pages()          │  ── reads fs ──┐  │
│  │  • search_pages()        │  ── reads fs ──┤  │
│  │  • get_page(path)        │  ── reads fs ──┤  │
│  │  • get_related(path)     │  ── parses md ─┤  │
│  │  • get_stats()           │  ── reads fs ──┤  │
│  └──────────────────────────┘                │  │
│                                              │  │
│  ┌──────────────────────────┐                │  │
│  │  knowledge_lab_service   │  ◄─────────────┘  │
│  │  (file I/O + search)     │                   │
│  └──────────────────────────┘                   │
│                                ┌──────────────┐ │
│                                │ knowledge/   │ │
│                                │  wiki/*.md   │ │
│                                │  raw/        │ │
│                                └──────────────┘ │
└──────────────────────────────────────────────────┘
```

**Data flow:**
1. Backend reads `knowledge/wiki/` directly from the filesystem (project root)
2. No database — the markdown files ARE the database
3. Search is in-memory keyword matching (no external dependencies)
4. Frontend fetches rendered content via REST API
5. Markdown rendering happens client-side using existing `react-markdown`

**Why filesystem-backed instead of MongoDB:**
- The wiki IS the source of truth — duplicating to MongoDB adds sync complexity
- Reads are infrequent (admin-only) — filesystem performance is sufficient
- Zero schema management — file structure IS the schema
- Direct editing via GitHub/IDE stays the primary authoring workflow

---

## 2. Backend Design

### 2.1 New File: `backend/routes/knowledge_lab.py`

```python
from fastapi import APIRouter, HTTPException, Depends, Query
from auth import get_admin_user
import os, re, glob, json
from pathlib import Path

router = APIRouter(prefix="/api/knowledge-lab", tags=["knowledge-lab"])

WIKI_DIR = Path(__file__).parent.parent.parent / "knowledge" / "wiki"
```

### 2.2 New File: `backend/services/knowledge_lab_service.py`

Core service with three responsibilities:

**a) File Discovery**
- Walk `knowledge/wiki/` recursively (flat files + `sources/` subdirectory)
- Return sorted list of pages with: `path` (URL-safe key), `title` (from H1), `source_summary` (boolean), `last_modified`

**b) Markdown Parsing**
- Extract `# Title` from first line
- Extract `## Related Pages` section → structured list of `{title, target}`
- Extract `**Sources:**` or source summary references
- Return full markdown content + metadata

**c) Search**
- On first request (or at startup), build an in-memory index:
  - For each file: `{path, title, content_snippet, keywords}`
  - Content is lowercased and tokenized
- Search algorithm:
  1. Split query into words
  2. Score each page: +10 per title match, +3 per word in content, +5 per word in Related Pages section
  3. Return top 20 sorted by score, with highlighted snippets
- Index is rebuilt when `GET /api/knowledge-lab/refresh` is called (or on first request with staleness check)

### 2.3 API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/knowledge-lab/pages` | Admin | List all wiki pages |
| `GET` | `/api/knowledge-lab/pages/{path}` | Admin | Get page content + metadata |
| `GET` | `/api/knowledge-lab/search?q=...` | Admin | Full-text keyword search |
| `GET` | `/api/knowledge-lab/pages/{path}/related` | Admin | Get related pages for a page |
| `GET` | `/api/knowledge-lab/stats` | Admin | KB statistics (page count, word count, last updated) |
| `POST` | `/api/knowledge-lab/refresh` | Admin | Rebuild search index |

### 2.4 Endpoint Specifications

#### `GET /api/knowledge-lab/pages`

```json
// Response 200
{
  "pages": [
    {
      "path": "pneumologie",
      "title": "Pneumologie",
      "category": "specialty",
      "last_modified": "2026-05-30T21:00:00Z",
      "word_count": 980,
      "source_pages": ["sources/kp-vorbereitung-amboss"]
    },
    {
      "path": "sources/kp-vorbereitung-amboss",
      "title": "KP Vorbereitung — Amboss Zusammenfassung",
      "category": "source",
      "last_modified": "2026-05-30T20:30:00Z",
      "word_count": 450,
      "source_pages": []
    }
  ],
  "total": 26
}
```

#### `GET /api/knowledge-lab/pages/{path}`

`path` is URL-safe key: `pneumologie`, `sources/kp-vorbereitung-amboss`, etc.

```json
// Response 200
{
  "path": "pneumologie",
  "title": "Pneumologie",
  "content": "# Pneumologie\n\n## Asthma bronchiale\n\n| Merkmal | Beschreibung |\n...",  // raw markdown
  "related_pages": [
    { "title": "Kardiologie", "path": "kardiologie", "description": "Dyspnoe Differenzialdiagnose" },
    { "title": "Notfallmedizin", "path": "notfallmedizin", "description": "Akute Dyspnoe, Reanimation" }
  ],
  "sources": [
    { "title": "KP Vorbereitung — Amboss Zusammenfassung", "path": "sources/kp-vorbereitung-amboss" }
  ],
  "category": "specialty",
  "last_modified": "2026-05-30T21:00:00Z",
  "word_count": 980
}
```

```json
// Response 404
{ "detail": "Page not found" }
```

#### `GET /api/knowledge-lab/search?q=keywords&limit=20`

```json
// Response 200
{
  "query": "diabetes neuropathie",
  "results": [
    {
      "path": "innere-medizin",
      "title": "Innere Medizin",
      "snippet": "...**Diabetes** mellitus...mikrovaskulär: Retinopathie, Nephropathie, **Neuropathie**...",
      "score": 26,
      "category": "specialty"
    },
    {
      "path": "neurologie",
      "title": "Neurologie",
      "snippet": "...diabetische Poly**neuropathie**...",
      "score": 8,
      "category": "specialty"
    }
  ],
  "total": 2
}
```

### 2.5 Security

- **All endpoints require admin auth** via `Depends(get_admin_user)` — same pattern as existing `admin.py`
- **Path traversal protection**: `path` parameter is validated against a whitelist of discovered files. Any `../`, `..\\`, absolute path, or path outside the `wiki/` directory returns 404.
- **No write endpoints** — the Knowledge Lab is read-only. Wiki editing remains via IDE/GitHub.
- **No user data exposed** — no MongoDB queries, no PII.

---

## 3. Frontend Design

### 3.1 New File: `frontend/src/pages/KnowledgeLabPage.jsx`

**Route:** `/knowledge-lab` (admin-only, inside `<Layout>`)

**Layout (3-column):**

```
┌─────────────────────────────────────────────────────┐
│ [Search...                              ]  Stats    │
├──────────┬──────────────────────────────────────────┤
│ Pages    │  # Pneumologie                            │
│          │                                           │
│ ☰ All    │  ## Asthma bronchiale                    │
│ ──────── │                                           │
│  📄      │  | Merkmal | Beschreibung |              │
│  Speclty │  |---------|-------------|               │
│  ─────── │  ...                                      │
│   anaes   │                                           │
│   chir    │  ────                                    │
│   derma   │  **Related Pages:**                      │
│   gastro  │  → Kardiologie — Dyspnoe DD              │
│   gyn     │  → Notfallmedizin — Reanimation          │
│   hno     │                                           │
│   infekt  │  **Sources:**                             │
│   inner   │  → KP Vorbereitung — Amboss Zusammenfass.│
│   kardio  │                                           │
│   neuro   │                                          │
│   nos     │                                          │
│   notf    │                                          │
│   ortho   │                                          │
│   paed    │                                          │
│   pharma  │                                          │
│   pneumo  │                                          │
│   psych   │                                          │
│   rechts  │                                          │
│   urolog  │                                          │
│ ──────── │                                           │
│  📄      │                                           │
│  Concept │                                           │
│   biostat │                                          │
│   dia     │                                          │
│   klin-unt│                                          │
│   praeven │                                          │
│ ──────── │                                           │
│  📄      │                                           │
│  Source  │                                           │
│   -austria│                                          │
│   -kp-... │                                          │
│          │                                           │
│ ──────── │                                           │
│  📁      │                                           │
│  Licensing                                           │
│   -nostri│                                          │
├──────────┴──────────────────────────────────────────┤
│ [Status: 26 pages · 3 sources · KB stable ✅]       │
└─────────────────────────────────────────────────────┘
```

### 3.2 Components

| Component | Responsibility |
|-----------|---------------|
| `KnowledgeLabPage` | Main page, layout orchestration |
| `KBSidebar` | Collapsible page tree with search input, category grouping |
| `KBPageViewer` | Renders markdown content via `MarkdownRenderer`, shows metadata bar |
| `KBSearchResults` | Search result list with highlighted snippets |
| `KBRelatedPages` | Panel showing linked pages (clickable) |
| `KBSourceRefs` | Panel showing source document references |

### 3.3 Frontend Data Flow

```
KnowledgeLabPage
├── useEffect → fetch /api/knowledge-lab/pages
├── useState · pages[], selectedPath, searchQuery, searchResults[]
│
├── onSearch(query) → fetch /api/knowledge-lab/search?q=... (debounced 300ms)
│   └── renders KBSearchResults instead of KBPageViewer
│
├── onSelectPage(path) → fetch /api/knowledge-lab/pages/{path}
│   └── renders KBPageViewer(content)
│   └── renders KBRelatedPages(related_pages)
│   └── renders KBSourceRefs(sources)
│
└── Sidebar filter: group pages by category (specialty / concept / source / licensing)
```

### 3.4 Reuse

- `MarkdownRenderer` already exists in `frontend/src/components/MarkdownRenderer.jsx` — fully reusable
- `Badge`, `Card`, `Input`, `ScrollArea` from existing shadcn/ui components
- `axios` / `apiClient` already configured

### 3.5 New Route

In `App.js`:
```jsx
import KnowledgeLabPage from "@/pages/KnowledgeLabPage";

<Route path="/knowledge-lab" element={
  <ProtectedRoute adminOnly><KnowledgeLabPage /></ProtectedRoute>
} />
```

---

## 4. Search Implementation Details

### 4.1 Index Structure (in-memory)

```python
# Built in knowledge_lab_service.py on startup + refresh
search_index = {
    "pages": [
        {
            "path": "pneumologie",
            "title": "Pneumologie",
            "title_lower": "pneumologie",
            "content_words": {"asthma": 3, "copd": 2, "lungenembolie": 1, ...},
            "total_words": 980,
            "related_titles": ["kardiologie", "notfallmedizin", "diagnostik"]
        },
        ...
    ]
}
```

### 4.2 Search Algorithm

```python
def search(query: str, index: dict, limit: int = 20):
    tokens = re.findall(r'\w+', query.lower())
    scored = []
    for page in index["pages"]:
        score = 0
        for token in tokens:
            # Title match (highest weight)
            if token in page["title_lower"]:
                score += 10
            # Content match
            score += page["content_words"].get(token, 0) * 3
            # Related page title match
            if token in " ".join(page["related_titles"]).lower():
                score += 5
        if score > 0:
            snippet = extract_snippet(page["raw_content"], query, 120)
            scored.append((score, page["path"], page["title"], snippet))
    scored.sort(reverse=True)
    return scored[:limit]
```

### 4.3 Performance

- Index build: ~5ms for 26 files (sub-millisecond per file)
- Search: O(n × m) where n = pages, m = query tokens. ~0.1ms for 26 pages × 3 tokens
- No external dependencies — pure Python string operations
- Index stored in module-level singleton, rebuilt on `POST /refresh`

---

## 5. Database Requirements

**None.**

All data comes from:
1. The filesystem (`knowledge/wiki/*.md`)
2. Parsed markdown metadata

This is intentional:
- No sync lag between file edits and UI
- No schema migrations
- Wiki can be developed independently (just edit markdown files)
- Reduces operational complexity

If caching becomes necessary (e.g., slow filesystem on Render's ephemeral storage), a simple in-memory cache with a staleness TTL (e.g., 60 seconds) can be added to the service layer without any database.

---

## 6. Security Considerations

| Risk | Mitigation |
|------|-----------|
| **Path traversal** | Validate `path` against discovered file list; reject `../` or absolute paths |
| **Unauthorized access** | All endpoints use `Depends(get_admin_user)`; same JWT pattern as existing admin routes |
| **Markdown injection** | `react-markdown` v9 does NOT render HTML by default; `dangerouslySetInnerHTML` is NOT used |
| **File content exposure** | Only `knowledge/wiki/` is served — restricted by path whitelist |
| **Rate limiting** | Existing `slowapi` limiter applies automatically; add specific limit for `/search` |
| **No write access** | No POST/PUT/DELETE that modifies files — read-only by design |
| **XSS via markdown links** | `MarkdownRenderer` opens links with `target="_blank" rel="noopener noreferrer"`; `disallowedElements` blocks script/iframe/object |

---

## 7. Estimated Implementation Effort

| Task | Hours | Dependencies |
|------|-------|-------------|
| Backend: service layer (file discovery, markdown parsing) | 2 | None |
| Backend: search index build + search algorithm | 1.5 | Service layer |
| Backend: router + 5 endpoints | 1 | Auth module |
| Backend: path traversal protection | 0.5 | — |
| Backend: tests | 1 | Router |
| Frontend: `KnowledgeLabPage` layout | 2 | Existing shadcn/ui |
| Frontend: `KBSidebar` with grouping + search input | 1.5 | Existing UI components |
| Frontend: search results view | 1 | API |
| Frontend: navigation highlighting, error states | 0.5 | — |
| Frontend: route registration in `App.js` | 0.25 | — |
| Integration testing (backend + frontend) | 1 | Both sides |
| **Total** | **~12 hours** | |

**Notes:**
- `MarkdownRenderer` already exists — no work needed
- `axios` / `apiClient` already configured — no work needed
- Auth module already provides `get_admin_user` — no work needed

---

## 8. Recommended MVP Scope

### MVP (Phase 1 — ~8 hours)

Deliverable: Working Knowledge Lab with basic browse + search + read.

| Feature | Included | Why |
|---------|----------|-----|
| List all pages | ✅ | Core navigation |
| Search by keyword | ✅ | Core feature |
| Read page content | ✅ | Core feature |
| Show related pages | ✅ | Low effort, high value |
| Show source references | ✅ | Low effort, high value |
| Sidebar grouping | ✅ | Baseline UX |
| Search result snippets | ✅ | In MVP |
| Loading/error states | ✅ | Hard requirement |
| Mobile responsive | ❌ | Desktop-first admin feature; mobile can be follow-up |
| `GET /stats` endpoint | ❌ | Nice-to-have — shows page count, word count, freshness |
| `POST /refresh` endpoint | ❌ | Index auto-rebuilds on first request after file change; explicit refresh is optional |

### Phase 2 (Post-MVP — ~4 hours)

- Mobile-responsive layout
- Stats dashboard (page count, last updated, coverage % vs sources)
- Scroll position persistence when navigating between pages
- Keyboard navigation (j/k to move between pages in sidebar)
- Dark mode consistency with existing theme

---

## 9. Risks & Challenges

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Render ephemeral filesystem** — `knowledge/` may not be deployed | Medium | High — backend can't find files | Verify `knowledge/` is included in the Render deployment build. If not, either (a) copy into the backend Docker image, or (b) include `knowledge/` in the deploy path. The directory is already in the repo, so standard deployment should include it. |
| **Markdown parsing edge cases** — table-heavy pages, multi-line links | Low | Medium | Test with 3–5 representative pages. The extracted `Related Pages` regex may miss edge cases (nested parens, reference-style links). |
| **Search quality** (simple keyword may miss relevant pages) | Medium | Low | Phase 1 is intentionally simple. If users report poor results, add stemming (PyStemmer) or fuzzy matching. No architectural change needed. |
| **Search index staleness** — files edited via IDE but index is outdated | Low | Low | Index rebuilds on each search request if the file modification timestamps changed. This is a simple `max(mtime)` check at search time. |
| **Conflict with existing `rag/` routes** — naming collision | Low | Medium | Using `/api/knowledge-lab/` prefix isolates it. Verify no existing route conflicts. |
| **File encoding issues** — Windows vs Unix line endings in markdown | Low | Low | Python's `open()` handles both. Verify with `utf-8` encoding parameter. |

---

## 10. Decision Points

### A. Markdown rendering: server-side vs client-side

**Recommendation: Client-side.**

The existing `MarkdownRenderer` with `react-markdown` + `remark-gfm` already supports tables, lists, code blocks, and links. Transmitting raw markdown over the wire is ~30% smaller than HTML. Client-side rendering is the standard pattern for this stack.

### B. Search index: in-memory vs SQLite

**Recommendation: In-memory.**

~26 pages × 500 words each ≈ 13,000 words. An in-memory dict is far simpler than SQLite and performs well at this scale. If the wiki grows to 100+ pages with 200,000+ words, a lightweight FTS5 SQLite index can be swapped in behind the same service interface.

### C. Path format: filename-based vs slug-based

**Recommendation: Filename-based (minus `.md`).**

`pneumologie` → `pneumologie.md`, `sources/kp-vorbereitung-amboss` → `sources/kp-vorbereitung-amboss.md`. This maintains a 1:1 mapping with the filesystem, avoids slug generation complexity, and makes URLs predictable from filenames.
