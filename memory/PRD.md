# Prep Academy - PRD

## Architecture
- Frontend: React + Tailwind + Shadcn (PWA)
- Backend: FastAPI + MongoDB
  - server.py (~3600 lines), routes/{admin, learn, billing, daily_podcast, rag}.py, telegram_bot.py
- AI stack (cost-optimised, open-source first):
  - **RAG**: ChromaDB (local) + BGE-M3 (local, 2.2GB, multilingual) + DeepSeek V3.1 via OpenRouter (~$0.15/M tokens)
  - LLM fallback: Qwen3 235B (via OpenRouter)
  - TTS: Microsoft Edge TTS (FREE, multi-lingual, 2-speaker podcasts)
  - Vision (Analyzer): Qwen-VL / Nemotron via OpenRouter
- Design: Royal Blue (#0c1229) + Matte Gold (#c9a84c)
- Env cache: HF_HOME=/tmp/hf_cache (large overlay volume — the 10GB /app volume is insufficient for BGE-M3)

## Recent (May 1, 2026) — DICOM Quality Gate (input validation)
- **Principle: "Garbage in → Garbage out"** — reject bad input BEFORE analysis pipeline
- `_check_quality_gate()` in `/app/backend/routes/dicom.py` rejects on upload:
  - **Secondary Capture modalities** (OT/SC/PR/KO/SR) or SecondaryCapture SOP Class UID
  - **Cross-sectional modalities (CT/MR/PT/NM) with < 5 slices**
  - Returns HTTP 422 with `{code, reason, action, modality, slice_count}`
- **Single-slice projection imaging accepted** (CR/DX/MG/XA/RF/US/ES) — single X-ray is valid
- Missing Modality → soft warning in `quality_warning` field (does NOT reject)
- Frontend shows toast with reason + recommended action when upload is rejected

## Recent (May 1, 2026) — DICOM Phase 2 Context-Aware (gatekeeper)
- **BODY_PART_CONTEXT** — 7 regions (chest/brain/abdomen/pelvis/spine/limb/unknown) with per-region allowed_conditions, rag_categories, icd10_prefixes (including R-codes), forbidden_terms, German label.
- **Hybrid body-part detection**: DICOM metadata (99% conf) → keyword match on descriptions (85%) → image aspect-ratio heuristic (55%) → fallback (unknown).
- **GATEKEEPER: "No context = No analysis"** — if body_part=='unknown' AND no manual override, the job returns status='context_missing' WITHOUT calling LLM. Returns `valid_regions` list to UI.
- **Manual body-part override** — `body_part_override` in AnalyzeRequest (chest/brain/abdomen/pelvis/spine/limb). Sets detection.method='manual_override' conf=1.0.
- **Dynamic region-constrained prompt** — LLM receives allowed/forbidden pathology lists for the specific body part, preventing cross-region hallucinations.
- **RAG category filter** — ChromaDB `where={"category": {"$in": ctx.rag_categories}}` with graceful fallback.
- **Validation layer** — forbidden-term check + ICD-10 prefix check. On failure: flags stored + urgency downgrade.
- **Confidence gate** — confidence < 0.5 → urgency downgraded to LOW with warning in explainability.
- **Frontend** — new detection banner (data-testid='dicom-detection-banner', 'dicom-body-part', 'dicom-validation-ok'/'-failed'); region-override buttons (data-testid='dicom-region-auto'/'-chest'/'-brain'/'-abdomen'/'-pelvis'/'-spine'/'-limb'); context_missing warning (data-testid='dicom-context-missing').
- Tested live: chest DCM → J18/R09.1/J90 (valid); brain DCM → I61/S06.0 (valid); no-hint DCM → hard-stop at context_missing, then override='chest' succeeds.

## Recent (May 1, 2026) — DICOM Phase 1 Quick Wins + Async Architecture
- **Structured AI Output** — analyze returns `analysis.structured = {findings, urgency, confidence, red_flags, explainability, icd10}`
- **Smart Sampling Upgrade** — Shannon entropy added to saliency formula
- **Risk Scoring UI** — red/amber/green urgency banner with Flame/AlertTriangle/Info icons + confidence %
- **Explainability Section** — amber card explaining WHY this urgency level (numbered reasons with slice refs)
- **PDF Report Download** — `GET /api/dicom/report-pdf/{id}` using fpdf2 with DejaVu Unicode, coloured urgency banner, red flags, explainability, sources, Haftungsausschluss
- **Hospital Mode (lite)** — `GET /api/dicom/timeline/{patient_label}` aggregates all scans per patient with urgency_summary; history list shows urgency badges inline
- **Async Polling Architecture** — `POST /api/dicom/analyze/{id}` now returns in <1s with status='analyzing' and spawns `asyncio.create_task(_run_analysis_job)`. Frontend polls `GET /api/dicom/{id}` every 2.5s. This permanently eliminates the k8s 60s ingress timeout (iteration_40 PASS 100% frontend, PDF + all structured data working).
- Fixed: regex-based marker stripping (no more STRUCTURED_JSON/CROSS_CHECK_JSON leaking into displayed report)

## Recent (May 1, 2026) — DICOM Pipeline
- **DICOM Analysis (100% open-source)** — pydicom + OpenCV + RAG + DeepSeek
  - Endpoints: POST /api/dicom/upload (.dcm OR .zip series), POST /api/dicom/analyze/{id},
    GET /api/dicom/{id}, GET /api/dicom/list/mine, POST /api/dicom/compare/{id1}/{id2}
  - Smart Sampling: Canny edge density + hyperdense/hypodense contour count → top-K slices (no AI)
  - Numerical feature extraction (saliency, variance, bright/dark regions per slice)
  - Clinical report via DeepSeek V3.1 grounded in RAG KB with [1], [2] citations mapped to sources
  - Cross-Verification Agent (embedded JSON in single LLM call — saves 1 roundtrip)
  - Patient Longitudinal Tracking — compare two scans with quantitative delta + progression report
  - Nursing Care Plan auto-generated as section 5 of the report
  - New /dicom React page with upload → previews → analyze → report + history/compare UI
  - Test: backend 12/12 pytest pass; analyze latency tuned to 43s (< 60s ingress limit)

## Recent (May 1, 2026) — Medical RAG
- ChromaDB + BGE-M3 + DeepSeek V3.1

## Previous Major Work
- Medical Analyzer: multipart upload (avoids ingress size limits), OpenRouter Qwen-VL + Nemotron
- Multi-language Edge-TTS Podcast: 5 languages, 2-speaker (Moderator/Experte), FREE
- Daily 5-min Medical Podcast: cron-like background job pulling real MCQs from DB
- Stripe (Test Mode) billing / Premium page (country-limited — PayPal/NOWPayments still pending)
- PDF MCQ Extraction: 442 questions (Q525-Q1075) parsed but NOT YET imported to DB

## Backlog (Prioritized)
- P0 Import 442 extracted MCQs to MongoDB `questions` collection (~10 min)
- P0 PayPal or NOWPayments (Crypto) alternative to Stripe (Egypt-friendly)
- P1 server.py refactor (extract Gamification, Dashboard, AI Chat into separate route files)
- P1 Expand RAG KB with PubMed abstracts + S3-Leitlinien PDF batch ingest
- P2 User-specific fine-tuning on wrong answers
- P2 Hybrid retrieval (BM25 + vector) for rare medical terms
- P3 React Native / Capacitor mobile app

## Credentials
- Admin: admin@medical.com / admin123

## Complete Feature List (28 features)
1-25: Previous features all working (see iteration 35 audit)
26. AI Medical Blog — Auto-generated SEO articles, public /blog
27. Smart Audio Podcast — 2-step summary → 2-speaker podcast
28. **Medical RAG (NotebookLM alternative)** — ChromaDB + BGE-M3 + DeepSeek V3.1 with citations [N]


## Recent (Apr 27, 2026) — DAILY PODCAST + QUIZ TTS 🎙️
- **Daily 5-min Podcast** auto-generated for 5 languages every 6 hours via Qwen3-235B-2507 + Edge TTS
  - Public page `/podcast` with player, language switcher, history, MP3 download
  - "Daily" link added to nav (Headphones icon)
  - Background loop in `routes/daily_podcast.py` runs forever from server startup
  - Idempotent per (date, language) — won't regenerate if already exists today
  - Admin manual trigger: `POST /api/podcast/admin/generate`
  - Tested: German Pediatric case "RSV Bronchiolitis" — 4:32 audio, 2.1MB MP3, 71s generation
- **Quiz TTS "Read Aloud"** — `POST /api/learn/tts/speak` (single-voice, fast)
  - Volume button on every quiz question (top-right of card)
  - Reads question + all answer choices aloud
  - 2-second response time (Edge TTS Austrian Ingrid voice)
  - Auto-stops when navigating to next question
- Fixed Qwen model ID: `qwen/qwen3-235b-a22b-2507` (cheapest text-only at $0.0000001/token)

## Recent (Apr 27, 2026) — Multi-Language Podcast
- Podcast supports DE/EN/AR/RU/UK with native voices
- Language-aware speaker tag detection

## Recent (Apr 27, 2026) — Earlier Today
- Edge TTS replaces broken OpenAI TTS
- Stripe Billing (test mode), 3 packages
- Medical Analyzer uses Qwen3-VL + Nemotron Vision (open source)

## Backlog
### P1
- Continue route extraction
- Weekly Leaderboard with badges
- Landing Page redesign with testimonials
### P2
- More blog articles auto-generation
- Daily scheduled blog posts
### P3
- Stripe, Mobile App
