# Codebase Audit Report — prep-academy

Date: 2026-06-19
Scope: Security, test coverage, documentation, architecture.
Method: Four parallel review agents over the working tree at `C:\Users\Metwaky\prep-academy`.

---

## Executive Summary — Fix in This Order

1. **Stripe webhook has zero tests** (`backend/routes/billing.py:228`). Money-handling code without webhook signature, idempotency, or refund tests.
2. **Stored XSS via SVG upload** (`backend/routes/question_images.py:26`). `.svg` accepted with no sanitization; raw bytes written to disk.
3. **Root `.AGENTS.md` documents a different project** (TELC C1 trainer). Actively misleads every contributor and AI agent. No root `README.md` exists.
4. **`backend/server.py` is 8,800 lines with ~120 inline route handlers** mixing routing, DB, and LLM logic. Bottleneck for testability, onboarding, and every other refactor.
5. **CI runs only 8 of 60 backend test files**; the other 52 never execute on PR. `conftest.py` silently skips the suite when the live admin login fails.

Everything else is downstream of these.

---

## 1. Security Audit

### Verified non-issues
- `.env` files are **not** tracked in git (`backend/.env`, `MiMo-Code/.env`, `.env.local`).
- `backend/auth.py` JWT + bcrypt implementation is sound.
- `backend/database.py` refuses startup on missing/weak `JWT_SECRET` (<32 chars or legacy default).
- `backend/services/url_validator.py` SSRF protection is correctly implemented (RFC-1918 blocklist).
- DICOM ZIP handling is **not** zip-slip vulnerable — `backend/routes/dicom.py` reduces filenames to `os.path.basename()` and reads in-memory.

### High
- **Stored XSS via SVG upload** — `backend/routes/question_images.py:26` allows `.svg` in `ALLOWED_EXT`; `_save_bytes` writes raw bytes with no sanitization. No `defusedxml` / `bleach` / `nh3` anywhere in the route. Attacker uploads SVG with `<script>` payload, every viewer of that question is pwned.
  - **Fix:** strip scripts via `defusedxml.ElementTree` on upload, or normalize-to-PNG via Pillow.

### Medium
- **Over-permissive CORS** — `backend/server.py:8788-8794` has a correct origin allowlist but pairs it with `allow_methods=["*"]`, `allow_headers=["*"]`.
  - **Fix:** tighten to the methods/headers actually used.
- **Decompression-bomb risk in DICOM ZIP** — `backend/routes/dicom.py` has no uncompressed-size cap.
  - **Fix:** cap total uncompressed size (~200 MB) and per-file (~50 MB) before reading.
- **Prompt-injection surface in `backend/metsu.py`** — untrusted text fed to multiple LLMs in the consensus pipeline without input sanitization or output validation guards.
  - **Fix:** add an input allowlist, output schema validation, and refuse to act on instructions found in user content.

### Top 3 to fix first
1. SVG sanitization on `question_images.py` upload.
2. ZIP decompression-bomb cap on `dicom.py`.
3. CORS method/header tightening on `server.py:8788-8794`.

---

## 2. Test Coverage Audit

### State of testing
- ~60 backend pytest files; **~95% are HTTP-driven smoke tests** hitting a remote preview host (`emergentagent.com`). Not isolated units.
- Only 8 files use `mock` / `patch` / `MagicMock`.
- CI (`.github/workflows/ci.yml`) runs **only 8 of 60** backend test files and **no frontend tests at all** (frontend build only, no `npm test`).
- Frontend: 3 trivial tests under `frontend/src/components/tutor/__tests__/` against 51 page components + 25 top-level components.
- No coverage gate anywhere in the repo.
- Root-level Puppeteer scripts (`test_e2e.js`, `test_homepage.js`, `test_community_ui.js`, `test_prod.js`) exist but are not wired to any runner or CI.

### Well-covered
- RAG pipeline: `test_rag.py`, `test_rag_improvements.py`, `test_rag_citation_filtering.py`, `test_unified_rag_boundaries.py`, `test_obsidian_rag_benchmark.py`, `test_extraction_benchmark.py`.
- Analyzer + DICOM: 9 analyzer files, 5 DICOM files (benchmarks, redteam, safety, access control).
- Community/moderation: `test_community.py`, `test_community_integration.py`, `test_moderation_orchestrator.py`.
- Admin access control via FastAPI `TestClient`: `test_admin_endpoint_access_control.py`, `test_dicom_access_control.py`.
- Knowledge-lab parser: `test_knowledge_lab_parser.py`.

### Critical gaps
- **`backend/routes/billing.py` — zero dedicated tests.** Stripe checkout + `/webhook/stripe` handler mutates `subscription_tier` / `premium_until`. No webhook-signature test, no idempotency test, no failed-payment/refund test. **Highest-risk untested code in the repo.**
- **`backend/auth.py` primitives untested in isolation** — `hash_password`, `verify_password`, `create_token`, `decode_token` (incl. `ExpiredSignatureError` / `InvalidTokenError` branches). Only end-to-end via login flows.
- **`backend/scoring.py` has no dedicated test file** — grading logic exercised only transitively via `test_api.py`, `test_sm2_seo_notifications.py`.
- **Frontend pages effectively untested** — `QuizPage`, `ExamSimulationPage`, `BillingPage`, `LoginPage`, `RegisterPage`, `AdminPage`, `CommunityPage`, custom hooks (`useAIChat`, `useConversations`, `useFeed`, `useMessages`), and the `Layout`/`ErrorBoundary` shell.
- **No API contract tests** (no Schemathesis / Pact / OpenAPI validation).
- **No real E2E in CI.**

### Quality red flags
- `backend/tests/conftest.py` hard-codes `admin@medical.com / admin123` against a remote host; if auth fails the whole suite silently `pytest.skip`s. Green CI can mean "everything skipped."
- 60+ scattered `pytest.skip(...)` inside test bodies (e.g. `test_notebook_ai_tools.py` skips ~10 if a specific notebook ID is absent).
- `backend/tests/test_rag_improvements.py` defaults `BASE_URL` to a hard-coded preview URL.
- Multiple tests only assert `status_code in (200, 400)` (e.g. `test_rag_improvements.py::test_pdf_ingest_empty`) — not a meaningful assertion.
- `frontend/package.json` has no `test:ci` script, no coverage thresholds, no Jest `collectCoverageFrom`.

### Top 3 recommendations
1. **Hermetic Stripe/billing tests** using FastAPI `TestClient` + a mocked `StripeCheckout`. Cover: bad signature → 400, duplicate webhook idempotency, successful charge flips `subscription_tier` + `premium_until`, refund downgrades. Target: `backend/routes/billing.py:228` webhook.
2. **Stop running tests against the remote preview host.** Refactor `backend/tests/conftest.py` to use `TestClient` + `mongomock` (or a CI-side Mongo service). Convert the high-value HTTP tests (`test_api.py`, `test_gamification_auth.py`, `test_rag_improvements.py`). Expand CI from 8 files to the full suite and fail on `skip` rate > 5%.
3. **Real frontend testing.** Add `frontend/jest` config with `collectCoverageFrom: ["src/**/*.{js,jsx}"]` and a coverage threshold (start 20%, ramp). Tests for `LoginPage`, `RegisterPage`, `QuizPage`, `BillingPage`, and the `useAIChat` / `useConversations` hooks. Wire `npm test -- --watchAll=false --coverage` into `.github/workflows/ci.yml`. Promote `test_e2e.js` to a Playwright PR smoke.

---

## 3. Documentation Audit

### Onboarding readiness — 3/10
A new engineer cannot get productive in a day.

- No root `README.md`.
- Root `.AGENTS.md` documents a *different* project (TELC C1 German speaker trainer with Groq) — **actively misleading**.
- `frontend/README.md` is unmodified Create React App boilerplate.
- No documented quickstart (`npm install` / `pip install` / `docker compose up`).
- No single env-var reference; vars scattered across `BETA_READINESS.md`, `DEPLOYMENT_BRIEF.md`, `DEPLOY_GUIDE.md` (Arabic), `render.yaml`.

### What exists and is good
- `ARCHITECTURE_REVIEW.md` — accurate, current topology + route table + AI pipeline notes. **Best onboarding doc in the repo.**
- `docs/rag.md`, `docs/obsidian-rag-integration.md`, `docs/final-rag-architecture.md`, `docs/production-smoke.md`, `docs/dicom.md` — focused, living technical docs that map to real code.
- `knowledge/CLAUDE.md` + `knowledge/AGENTS.md` — well-scoped vault editorial contract (subdir-only).
- FastAPI auto-generates `/docs` and `/redoc` in non-production (`backend/server.py:78-81`).

### Critical gaps
- No root `README.md`.
- Root `.AGENTS.md` is for the wrong project — **delete or rewrite immediately**.
- No env-var reference; no `backend/.env.example`.
- No code-level docstrings — `server.py` (8,827 lines) has only 247 `"""` markers; `metsu.py`, `routes/learn.py`, `auth.py`, `scoring.py`, `models.py` have no docstrings on public functions.
- No runbook (incident response, log locations, rollback for partial Render/Vercel/Atlas failures).
- No `CONTRIBUTING.md`, no `LICENSE`.

### Doc debt — the recently-added MD pile
Mostly one-shot planning noise cluttering the repo root.

| File | Action |
|---|---|
| `WAVE1_FEEDBACK_REPORT.md`, `WAVE1_FEEDBACK_TEMPLATE.md`, `WAVE1_ISSUE_TRACKER.md`, `WAVE1_MANUAL_CHECKS.md` | Archive → `docs/archive/wave1/` |
| `PHASE2A_PLAN.md`, `PHASE2_DESIGN_PROPOSAL.md`, `EXECUTION_ROADMAP.md` | Archive → `docs/archive/phase2/` |
| `BETA_READINESS.md`, `LAUNCH_CHECKLIST.md`, `DEPLOYMENT_BRIEF.md`, `DEPLOY_GUIDE.md` | Merge → `docs/deployment.md` + `docs/runbook.md` (`DEPLOY_GUIDE.md` contradicts the others with `CORS_ORIGINS=*` and different DB names) |
| `ARCHITECTURE_REVIEW.md` | Promote → `docs/architecture.md`, keep current |
| `production_bible.md` | Misleading name — it's a video promo script. Rename → `marketing/promo-script.md` |
| `.AGENTS.md` (root) | Delete or fully rewrite — wrong project |
| `OMAR_KHASAN_PRO.docx`, `UsersMetwakyOMAR_KHASAN_PRO_NEW.docx`, `landing.html`, `landing_light.html`, debug PNGs | Move out of repo root |

### Top 3 recommendations
1. **Write a root `README.md`** (50–100 lines): one-paragraph product description, stack diagram (steal from `ARCHITECTURE_REVIEW.md`), `docker compose up` quickstart, links to `docs/architecture.md`, `docs/deployment.md`, `docs/runbook.md`. Replace `.AGENTS.md` with one that points here.
2. **Consolidate the deployment pile** into `docs/deployment.md` + `docs/runbook.md`; archive 7+ phase/wave files under `docs/archive/`. Add `backend/.env.example` as the single source of truth.
3. **Module-level docstrings on the top 10 backend hotspots** — `server.py`, `metsu.py`, `auth.py`, `scoring.py`, every file in `routes/`. One paragraph each explaining "what this owns and what it depends on."

---

## 4. Architecture Review

### System shape
```
┌─────────────────────┐      ┌─────────────────────────────────┐
│   Vercel (SPA)      │─────►│   Render (FastAPI / uvicorn)    │
│   React + shadcn    │      │   server.py (~8,800 lines)      │
│                     │      │   + 20 route modules            │
└─────────────────────┘      └──────┬──────────┬──────────┬───┘
                                    │          │          │
                             ┌──────▼──┐  ┌───▼────┐  ┌──▼────────┐
                             │ MongoDB  │  │ Qdrant │  │OpenRouter │
                             │ (Atlas)  │  │(Cloud) │  │ (AI/Embed)│
                             └─────────┘  └────────┘  └───────────┘
```
Single-process FastAPI monolith. Business domains registered via `include_router` at the bottom of `server.py`. Background loops run as `asyncio.create_task` inside the uvicorn event loop (no separate worker).

### Strengths
- Async Motor throughout — no thread-pool blocking on DB.
- `slowapi` rate limiting, correlation IDs via `contextvars`, global exception handler.
- SSE streaming actually implemented (`/ai/tutor/stream`).
- Retrieval converging on `services/retrieval_orchestrator.py` — hybrid BM25+vector, CrossEncoder reranker, clean `RetrievalRequest` dataclass. Legacy ChromaDB gated off behind `ENABLE_LEGACY_CHROMA=false`; Qdrant is live.
- `ENABLE_ADVANCED_FEATURES` flag gates heavy deps (`sentence-transformers`, `chromadb`, `opencv`).
- MongoDB indexes are comprehensive — TTL for logs, partial for hash dedup, compound for hot queries.
- Hard secrets guard in `database.py`.

### Structural weaknesses

| Severity | Issue | Location |
|---|---|---|
| High | `server.py` is 8,800 lines with ~120 inline route handlers mixing routing, DB calls, LLM calls, and response construction. No service layer for inline code. | `backend/server.py` |
| Medium | Synchronous CPU-bound `fitz.open()` PDF parsing inside `async def` handlers — blocks the event loop. | `backend/server.py:1881, 5310, 5645` |
| Medium | Background loops (daily podcast, trial, Obsidian watcher, data retention) run as unsupervised `asyncio.create_task`. Unhandled exception silently kills the task; no restart, no health reporting. | `backend/server.py` startup |
| Medium | No structured external observability — no Sentry, no OpenTelemetry, no metrics endpoint. AI pipeline errors surface only via `logger.error(f"...")`. | repo-wide |
| Medium | No repository abstraction for MongoDB — direct `db.collectionname` everywhere. Testing without a live Mongo requires patching the global `db` object. | repo-wide |
| Low-Med | OpenRouter client patterns duplicated across `server.py`, `metsu.py`, `embeddings.py`, route files — each reimplements retry/backoff/headers. | multiple |
| Low | In-process LRU embedding cache (200 entries) in `embeddings.py` — works on single-instance Render but breaks silently if workers are scaled. | `backend/embeddings.py` |
| Low | JWT without refresh tokens — long-lived single token, re-login on expiry. | `backend/auth.py` |

### Scalability risk

- **At 10× traffic:** single uvicorn process is the first bottleneck. Metsu consensus (3–6 parallel LLMs, up to 30 s each) and PDF analysis hold event-loop tasks open for the full duration; concurrent load exhausts the connection pool before DB or LLM APIs saturate. Render single-instance has no horizontal scaling; adding workers requires extracting background loops + in-memory caches.
- **At 100× content volume:** Qdrant uses one `tutor_chapters` collection with no metadata partitioning — all queries scan the full collection. Image manifest is a JSON file loaded into a module-level cache at request time (`backend/server.py:4340`) — at 10k images this is a cold-start problem.

### Top 3 architectural priorities
1. **Extract `server.py` inline handlers into `routes/` + thin service modules.** The 20 registered sub-routers are already the right pattern; the ~120 inline handlers (auth, questions/quiz, dashboard, AI tutor, admin batch) need to follow. Single change that unblocks testability, onboarding, and future service splits.
2. **Move CPU-bound work off the event loop.** Wrap `fitz.open()`, CrossEncoder reranking, and Metsu fan-out in `asyncio.run_in_executor`, or — for Metsu consensus — push to background jobs via the existing `services/ingestion_jobs.py` pattern.
3. **Single `services/openrouter_client.py`** with shared retry + per-call logging (model, latency, tokens, status). Replaces five independent re-implementations and gives the team the data to detect model degradation and cost spikes. Plug Sentry into `global_exception_handler` — one line, immediate production-error visibility.

---

## Consolidated Priority Order

| # | Action | Why | Where |
|---|---|---|---|
| 1 | Write hermetic Stripe/webhook tests | Money-handling code, zero tests | `backend/routes/billing.py:228` |
| 2 | Sanitize SVG uploads | Stored XSS live in production | `backend/routes/question_images.py:26` |
| 3 | Delete or rewrite root `.AGENTS.md`; write root `README.md` | Misdirects every contributor + agent | repo root |
| 4 | Cap DICOM ZIP decompression size | Decompression-bomb DoS | `backend/routes/dicom.py` |
| 5 | Tighten CORS methods/headers | Defense-in-depth | `backend/server.py:8788-8794` |
| 6 | Refactor `conftest.py` off remote host; expand CI to full suite | Green CI currently means nothing | `backend/tests/conftest.py`, `.github/workflows/ci.yml` |
| 7 | Extract inline handlers from `server.py` into route modules | Every other refactor depends on this | `backend/server.py` |
| 8 | Move PDF/Metsu CPU-bound work off the event loop | Concurrency bottleneck | `backend/server.py:1881, 5310, 5645`, `backend/metsu.py` |
| 9 | Consolidate deployment markdown pile; add `backend/.env.example` | One source of truth for ops | repo root → `docs/` |
| 10 | Add Sentry + a shared OpenRouter client | Observability + cost control | `backend/services/openrouter_client.py` (new), `backend/server.py` |

---

*Generated 2026-06-19 by parallel review of security, test coverage, documentation, and architecture surfaces.*
