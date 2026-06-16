"""
Medical RAG (Retrieval-Augmented Generation) System
====================================================
- Active Retrieval: Unified RAG layer via services.retrieval_orchestrator
- Vector Store: Qdrant only for active production retrieval
- Embeddings: shared provider from embeddings.py for all active sources
- Hybrid Search: vector candidates plus lexical scoring in one layer
- Reranking: unified CrossEncoder reranking when available
- LLM: DeepSeek-V3 via OpenRouter (cheap, high-quality)
- Knowledge Base: medical PDFs, tutor docs, and Obsidian notes
- Hallucination guard, prompt injection protection, query expansion
- Legacy Chroma: deprecated, read-only compatibility only when explicitly enabled

The models are lazy-loaded on first request to keep the server's startup fast
and the health-check responsive.
"""
import hashlib
import re as _re
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Tuple
import os
import uuid
import asyncio
import json
from datetime import datetime, timezone

import io

from database import db, logger
from auth import get_current_user, get_admin_user
from limiter import limiter
from services.obsidian_rag import (
    get_obsidian_status,
    reindex_obsidian_vault,
    search_obsidian,
    sync_obsidian_vault,
)
from services.ingestion_jobs import (
    create_job,
    get_job,
    list_jobs,
    start_job,
    status_summary,
    update_job_progress,
)
from services.retrieval_orchestrator import RetrievalRequest, retrieve as unified_retrieve
from vector_store import (
    count_unified,
    delete_unified,
    list_unified_source_versions,
    list_unified_sources,
    upsert_unified_chunks,
)

router = APIRouter(prefix="/api/rag", tags=["rag"])

# ───────────────────────── CONFIG ─────────────────────────
_CHROMA_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".chroma")
CHROMA_DIR = os.environ.get("CHROMA_DIR", _CHROMA_DEFAULT)
COLLECTION_NAME = "medical_kb"
PRIMARY_EMBED_MODEL = os.environ.get("RAG_EMBED_MODEL", "BAAI/bge-m3")
FALLBACK_EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
CROSSENCODER_MODEL = os.environ.get("RAG_CROSSENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
ENABLE_LEGACY_CHROMA = os.environ.get("ENABLE_LEGACY_CHROMA", "false").lower() in ("1", "true", "yes")
LEGACY_CHROMA_READ_ONLY = os.environ.get("LEGACY_CHROMA_READ_ONLY", "true").lower() not in ("0", "false", "no")

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_LLM_MODEL = "openai/gpt-oss-120b:free"

RAG_CHUNK_SIZE = int(os.environ.get("RAG_CHUNK_SIZE", "512"))
RAG_CHUNK_OVERLAP = int(os.environ.get("RAG_CHUNK_OVERLAP", "50"))
QUERY_MAX_LENGTH = 2000

_RATE_LIMIT = "20/minute"

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|directives|commands)",
    r"(you\s+are\s+now|act\s+as\s+if\s+you\s+are|from\s+now\s+on\s+you\s+are)",
    r"system\s*:\s*(You\s+are|you\s+should|your\s+(task|role|purpose))",
    r"forget\s+(all\s+)?(previous\s+)?(instructions|context|guidelines)",
    r"override\s+(system|safety|guidelines|restrictions)",
]

# ───────────────────────── LAZY SINGLETONS ─────────────────────────
_embed_model = None
_chroma_client = None
_collection = None
_init_lock = asyncio.Lock()
_init_state: Dict[str, Any] = {"ready": False, "error": "", "model": ""}
_crossencoder = None
_crossencoder_lock = asyncio.Lock()

_redis_client = None
_redis_available = False
_EMBED_CACHE_TTL = 86400  # 24 hours

# ───────────────────────── MULTILINGUAL EXPANSION DICT ─────────────────────────
_MEDICAL_TERM_MAP = {
    "heart": "Herz coeur",
    "chest": "Brustkorb thorax poitrine",
    "brain": "Gehirn cerveau",
    "lung": "Lunge poumon",
    "kidney": "Niere rein",
    "liver": "Leber foie",
    "bone": "Knochen os",
    "blood": "Blut sang",
    "pain": "Schmerz douleur",
    "fever": "Fieber fièvre",
    "infection": "Infektion infection",
    "fracture": "Fraktur fracture",
    "tumor": "Tumor tumeur",
    "surgery": "Operation chirurgie",
    "diabetes": "Diabetes diabète",
    "hypertension": "Hypertonie hypertension",
    "stroke": "Schlaganfall accident vasculaire cérébral",
    "pneumonia": "Pneumonie pneumonie",
    "therapy": "Therapie thérapie",
    "diagnosis": "Diagnose diagnostic",
}

# ───────────────────────── REDIS ─────────────────────────
def _get_redis():
    global _redis_client, _redis_available
    if _redis_client is not None:
        return _redis_client
    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        _redis_available = False
        return None
    try:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(redis_url, decode_responses=True)
        _redis_available = True
        logger.info("[RAG] Redis cache enabled at %s", redis_url.split("@")[-1] if "@" in redis_url else redis_url)
        return _redis_client
    except Exception as e:
        _redis_available = False
        logger.warning("[RAG] Redis cache unavailable: %s", e)
        return None


async def _cache_embedding(key: str, vector: List[float]) -> None:
    r = _get_redis()
    if not r:
        return
    try:
        await r.setex(f"rag_embed:{key}", _EMBED_CACHE_TTL, json.dumps(vector))
    except Exception as e:
        logger.debug("[RAG] Cache set failed: %s", e)


async def _get_cached_embedding(key: str) -> Optional[List[float]]:
    r = _get_redis()
    if not r:
        return None
    try:
        raw = await r.get(f"rag_embed:{key}")
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.debug("[RAG] Cache get failed: %s", e)
    return None


_cache_hits = 0
_cache_misses = 0


async def _get_embedding_cached(text: str) -> Tuple[List[float], bool]:
    global _cache_hits, _cache_misses
    key = hashlib.sha256(f"{text}|{PRIMARY_EMBED_MODEL}".encode()).hexdigest()
    cached = await _get_cached_embedding(key)
    if cached is not None:
        _cache_hits += 1
        return cached, True
    _cache_misses += 1
    loop = asyncio.get_event_loop()
    vec = await loop.run_in_executor(None, lambda: _embed_texts([text])[0])
    asyncio.create_task(_cache_embedding(key, vec))
    return vec, False


def _load_embed_model_sync():
    from sentence_transformers import SentenceTransformer
    try:
        logger.info(f"[RAG] Loading primary embedding model: {PRIMARY_EMBED_MODEL}")
        return SentenceTransformer(PRIMARY_EMBED_MODEL, device="cpu"), PRIMARY_EMBED_MODEL
    except Exception as e:
        logger.warning(f"[RAG] Primary model failed ({e}), falling back to {FALLBACK_EMBED_MODEL}")
        return SentenceTransformer(FALLBACK_EMBED_MODEL, device="cpu"), FALLBACK_EMBED_MODEL


async def _ensure_initialized():
    global _embed_model, _chroma_client, _collection
    if not ENABLE_LEGACY_CHROMA:
        raise HTTPException(status_code=410, detail="Legacy Chroma RAG is disabled; use unified Qdrant RAG.")
    if _init_state["ready"]:
        return
    async with _init_lock:
        if _init_state["ready"]:
            return
        try:
            loop = asyncio.get_event_loop()
            _embed_model, model_name = await loop.run_in_executor(None, _load_embed_model_sync)
            _init_state["model"] = model_name

            import chromadb
            from chromadb.config import Settings
            os.makedirs(CHROMA_DIR, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(
                path=CHROMA_DIR,
                settings=Settings(anonymized_telemetry=False),
            )
            _collection = _chroma_client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )

            if _collection.count() == 0 and not LEGACY_CHROMA_READ_ONLY:
                await loop.run_in_executor(None, _seed_initial_kb)

            _init_state["ready"] = True
            _init_state["error"] = ""
            logger.info(f"[RAG] Ready. Model={model_name}, KB docs={_collection.count()}")
        except Exception as e:
            _init_state["error"] = str(e)
            logger.error(f"[RAG] Init failed: {e}")
            raise HTTPException(status_code=503, detail=f"RAG-System nicht bereit: {e}")


def _embed_texts(texts: List[str]) -> List[List[float]]:
    vecs = _embed_model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vecs.tolist() if hasattr(vecs, "tolist") else [list(v) for v in vecs]


# ───────────────────────── CROSSENCODER ─────────────────────────
async def _ensure_crossencoder():
    global _crossencoder
    if _crossencoder is not None:
        return
    async with _crossencoder_lock:
        if _crossencoder is not None:
            return
        try:
            from sentence_transformers import CrossEncoder
            loop = asyncio.get_event_loop()
            _crossencoder = await loop.run_in_executor(
                None, lambda: CrossEncoder(CROSSENCODER_MODEL, device="cpu")
            )
            logger.info("[RAG] CrossEncoder loaded: %s", CROSSENCODER_MODEL)
        except Exception as e:
            logger.warning("[RAG] CrossEncoder load failed (non-fatal): %s", e)


async def _rerank_with_crossencoder(query: str, sources: List[Dict]) -> List[Dict]:
    if not sources:
        return sources
    await _ensure_crossencoder()
    if _crossencoder is None:
        return sources
    pairs = [(query, s["content"]) for s in sources]
    try:
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(None, lambda: _crossencoder.predict(pairs))
        for s, sc in zip(sources, scores):
            s["rerank_score"] = float(sc)
        sources.sort(key=lambda s: s.get("rerank_score", 0), reverse=True)
    except Exception as e:
        logger.debug("[RAG] CrossEncoder predict failed: %s", e)
    return sources


# ───────────────────────── PROMPT INJECTION PROTECTION ─────────────────────────
def _sanitize_query(query: str) -> str:
    q = query.strip()
    if len(q) > QUERY_MAX_LENGTH:
        q = q[:QUERY_MAX_LENGTH]
    for pattern in _INJECTION_PATTERNS:
        if _re.search(pattern, q, _re.IGNORECASE):
            raise HTTPException(
                status_code=400,
                detail=f"Anfrage enthält nicht erlaubte Anweisungsmuster. Bitte formulieren Sie Ihre Frage medizinisch.",
            )
    return q


# ───────────────────────── HALLUCINATION GUARD ─────────────────────────
def _check_citations(answer: str, num_sources: int) -> Tuple[str, bool, float]:
    hallucination_detected = False
    def _replace_bad_citation(match):
        nonlocal hallucination_detected
        num = int(match.group(1))
        if num < 1 or num > num_sources:
            hallucination_detected = True
            return ""
        return match.group(0)

    cleaned = _re.sub(r"\[(\d+)\]", _replace_bad_citation, answer)
    cleaned = _re.sub(r"\s+", " ", cleaned).strip()
    num_valid = len(set(_re.findall(r"\[(\d+)\]", cleaned)))
    total_possible = num_sources
    coverage = num_valid / max(total_possible, 1)
    return cleaned, hallucination_detected, coverage


# ───────────────────────── QUERY EXPANSION ─────────────────────────
def _expand_query(query: str) -> List[str]:
    variants = [query]
    q_lower = query.lower()
    matched_terms = []
    for en_term, de_term in _MEDICAL_TERM_MAP.items():
        if en_term in q_lower:
            matched_terms.append(de_term)
    if matched_terms:
        expansion_suffix = " ".join(matched_terms)
        variants.append(f"{query} {expansion_suffix}")
        variants.append(f"{expansion_suffix} {query}")
    return variants[:3]


async def _embed_and_merge(query: str) -> Tuple[List[float], int]:
    variants = _expand_query(query)
    all_vectors = []
    for v in variants:
        vec, cached = await _get_embedding_cached(v)
        all_vectors.append((vec, cached))
    avg_vec = [sum(c) / len(all_vectors) for c in zip(*[v for v, _ in all_vectors])]
    cache_info = sum(1 for _, c in all_vectors if c)
    return avg_vec, cache_info


# ───────────────────────── SEED KNOWLEDGE BASE ─────────────────────────
def _seed_initial_kb():
    seed_docs = [
        {
            "content": "ICD-10 S06.0 (Commotio cerebri / Gehirnerschütterung): Leichte, gedeckte Kopfverletzung mit kurzzeitigem Bewusstseinsverlust (<30 min). Klinische Zeichen: Kopfschmerzen, Übelkeit, Erbrechen, Amnesie, Konzentrationsstörungen. Therapie: 24–48h Überwachung, Bettruhe, Analgesie (Paracetamol), keine NSAR bei intrakranieller Blutung. GCS-Monitoring engmaschig.",
            "metadata": {"source": "ICD-10-GM", "code": "S06.0", "category": "Neurologie", "language": "de"},
        },
        {
            "content": "ICD-10 S02 (Fraktur des Schädels und der Gesichtsschädelknochen): Umfasst Kalotten-, Schädelbasis- und Gesichtsfrakturen. Leitsymptome: Monokel-/Brillenhämatom, Rhinoliquorrhoe, Otoliquorrhoe, Hirnnervenausfälle. CT als Goldstandard. Antibiotische Prophylaxe bei offenen Frakturen oder Liquorleck (z. B. Ceftriaxon 2g/d). Neurochirurgische Konsultation.",
            "metadata": {"source": "ICD-10-GM / RKI", "code": "S02", "category": "Chirurgie", "language": "de"},
        },
        {
            "content": "ICD-10 S27.2 (Traumatischer Hämatopneumothorax): Gleichzeitiges Vorhandensein von Luft und Blut im Pleuraraum nach Thoraxtrauma. Leitsymptome: Dyspnoe, einseitig abgeschwächtes Atemgeräusch, hypersonorer Klopfschall oberhalb, gedämpfter darunter, Kreislaufinstabilität. Diagnostik: Thorax-Röntgen, Sonographie (eFAST), CT. Therapie: SOFORTIGE Thoraxdrainage (Bülau-Drainage, 4.–5. ICR, mittlere Axillarlinie, 24–28 Ch). Volumentherapie, ggf. Bluttransfusion, chirurgische Versorgung bei Massivblutung (>1500 ml).",
            "metadata": {"source": "WHO / ATLS Leitlinien", "code": "S27.2", "category": "Notfallmedizin", "language": "de"},
        },
        {
            "content": "ICD-10 I21 (Akuter Myokardinfarkt): Klinik: Retrosternaler Vernichtungsschmerz >20 min, Ausstrahlung in linken Arm/Kiefer, Dyspnoe, Kaltschweißigkeit. EKG: ST-Hebung (STEMI) in ≥2 benachbarten Ableitungen oder neuer LSB. Labor: Troponin I/T erhöht. Therapie (STEMI): MONA-BASH — Morphin, O2 (bei SpO2<90%), Nitrate, ASS 250mg + P2Y12-Inhibitor (Ticagrelor 180mg), Heparin, Statin. PCI innerhalb 90 min (door-to-balloon). Bei NSTEMI: GRACE-Score.",
            "metadata": {"source": "ESC Guidelines", "code": "I21", "category": "Kardiologie", "language": "de"},
        },
        {
            "content": "ICD-10 J18 (Pneumonie, Erreger nicht näher bezeichnet): CAP = ambulant erworbene Pneumonie. Leitsymptome: Fieber, produktiver Husten, Dyspnoe, Thoraxschmerz, Rasselgeräusche. Diagnostik: Röntgen-Thorax, CRP, PCT, Blutkulturen. CRB-65 zur Risikostratifizierung. Therapie ambulant: Amoxicillin 1g 3×tgl 5–7 Tage. Stationär: Ampicillin/Sulbactam + Makrolid. Schwer: Piperacillin/Tazobactam + Clarithromycin.",
            "metadata": {"source": "RKI / S3-Leitlinie", "code": "J18", "category": "Pneumologie", "language": "de"},
        },
        {
            "content": "ICD-10 E11 (Diabetes mellitus Typ 2): Chronische Hyperglykämie durch Insulinresistenz. Diagnose: HbA1c ≥6,5%, Nüchternglukose ≥126 mg/dl, oGTT-2h ≥200 mg/dl. Therapieziele: HbA1c <7%, RR <140/90, LDL <100 mg/dl. Erstlinien-Therapie: Metformin (Start 500mg, Ziel 2000mg/d). Zweitlinie: SGLT-2-Inhibitoren (Empagliflozin) bei kardiovaskulärem Risiko, GLP-1-Agonisten (Semaglutid) bei Adipositas.",
            "metadata": {"source": "DDG / ADA Guidelines", "code": "E11", "category": "Endokrinologie", "language": "de"},
        },
        {
            "content": "ICD-10 I63 (Hirninfarkt / Ischämischer Schlaganfall): Akutes fokales neurologisches Defizit durch Gefäßverschluss. FAST-Test (Face/Arms/Speech/Time). Diagnostik: sofortiges CT (Ausschluss Blutung), CT-Angio, ggf. MRT-DWI. Therapie: Zeit < 4,5h nach Symptombeginn → IV-Lyse mit rt-PA (Alteplase 0,9 mg/kg). Zeit <6h + großer Gefäßverschluss → Thrombektomie. Sekundärprävention: ASS 100mg, Statin, RR-Einstellung.",
            "metadata": {"source": "DGN S3-Leitlinie", "code": "I63", "category": "Neurologie", "language": "de"},
        },
        {
            "content": "ICD-10 K35 (Akute Appendizitis): Leitsymptome: Periumbilikaler Schmerz, der nach rechts unten (McBurney) wandert, Übelkeit, Fieber (>38°C), Anorexie. Klinische Tests: Blumberg (kontralateraler Loslass-Schmerz), Rovsing, Psoas-Zeichen. Labor: Leukozytose, CRP erhöht. Sonographie: Zielscheibenphänomen, Durchmesser >7mm. Therapie: Appendektomie (laparoskopisch bevorzugt) innerhalb 24h. Perioperative Antibiose (Cefuroxim + Metronidazol).",
            "metadata": {"source": "DGAV / Klinik-Leitlinien", "code": "K35", "category": "Chirurgie", "language": "de"},
        },
        {
            "content": "ICD-10 A41 (Sepsis): Lebensbedrohliche Organdysfunktion durch dysregulierte Immunantwort auf Infektion. qSOFA ≥2 (AF≥22, RR sys≤100, GCS<15). Septischer Schock: Laktat >2 mmol/l + Vasopressoren-Bedarf. Therapie (Sepsis-Bundle 1h): Blutkulturen, Laktat, Breitband-Antibiose (Piperacillin/Tazobactam), Kristalloid-Infusion 30 ml/kg, Noradrenalin bei MAP <65 mmHg, Quell-Kontrolle.",
            "metadata": {"source": "Surviving Sepsis Campaign 2021", "code": "A41", "category": "Intensivmedizin", "language": "de"},
        },
        {
            "content": "ICD-10 J45 (Asthma bronchiale): Chronisch-entzündliche Atemwegserkrankung mit reversibler Obstruktion. Leitsymptome: Giemen, Dyspnoe, Husten (nachts/morgens), Thoraxenge. Diagnostik: Spirometrie (FEV1/FVC <0,7, Reversibilität >12%), Bronchospasmolysetest, FeNO. Stufentherapie (GINA): Stufe 1 — ICS-Formoterol bei Bedarf. Stufe 3 — niedrig dosiertes ICS-LABA. Akuter Anfall: Salbutamol 4 Hub, Prednisolon 50mg, O2, Magnesiumsulfat iv.",
            "metadata": {"source": "GINA Guidelines", "code": "J45", "category": "Pneumologie", "language": "de"},
        },
        {
            "content": "ICD-10 N39.0 (Harnwegsinfektion, HWI): Unkompliziert bei Frauen: Dysurie, Pollakisurie, Harndrang. Diagnostik: U-Stix (Leukozyten, Nitrit pos.), Uricult. Therapie: Fosfomycin 3g Einmaldosis ODER Nitrofurantoin 100mg 2×tgl 5 Tage ODER Trimethoprim 200mg 2×tgl 3 Tage. Bei Pyelonephritis: Ciprofloxacin 500mg 2×tgl 7 Tage oder stationär Ceftriaxon 2g iv. Schwangerschaft: IMMER behandeln (Cefuroxim, Fosfomycin).",
            "metadata": {"source": "S3-Leitlinie Harnwegsinfektionen", "code": "N39.0", "category": "Urologie", "language": "de"},
        },
        {
            "content": "ICD-10 F32 (Depression, depressive Episode): Hauptsymptome (≥2 von 3, >2 Wochen): gedrückte Stimmung, Interesseverlust, Antriebsmangel. Zusatzsymptome: Konzentration, Selbstwert, Schuldgefühle, Suizidgedanken, Schlafstörung, Appetitverlust. Schweregradeinteilung nach ICD-10. Therapie: mild/mittel — Psychotherapie (KVT, IPT). Mittel/schwer — SSRI (Sertralin, Citalopram) + Psychotherapie. Suizidalität abfragen, stationär bei akuter Gefährdung.",
            "metadata": {"source": "S3-NVL Unipolare Depression", "code": "F32", "category": "Psychiatrie", "language": "de"},
        },
        {
            "content": "ATLS ABCDE-Schema (Advanced Trauma Life Support): A — Airway mit HWS-Immobilisation, B — Breathing (Atmung, O2, Spannungspneumothorax entlasten), C — Circulation (Blutungskontrolle, 2× großlumige iv-Zugänge, Volumen), D — Disability (GCS, Pupillen, BZ), E — Exposure (komplettes Entkleiden + Wärmeerhalt). Reevaluation nach jedem Schritt. FAST-Sonographie bei hämodynamischer Instabilität.",
            "metadata": {"source": "WHO / ATLS", "code": "ATLS", "category": "Notfallmedizin", "language": "de"},
        },
        {
            "content": "ERC Reanimationsleitlinie 2021 (Erwachsene): 30:2 Kompressions-Beatmungs-Verhältnis, Frequenz 100–120/min, Drucktiefe 5–6cm. Defibrillation bei Kammerflimmern/pulsloser VT (150–200J biphasisch). Adrenalin 1mg alle 3–5 min bei Asystolie/PEA. Bei VF refraktär: Amiodaron 300mg nach 3. Schock. Reversible Ursachen (4H und 4T): Hypoxie, Hypovolämie, Hypo-/Hyperkaliämie, Hypothermie; Herzbeuteltamponade, Thromboembolie, Toxine, Thoraxspannung.",
            "metadata": {"source": "ERC Guidelines 2021", "code": "CPR", "category": "Notfallmedizin", "language": "de"},
        },
        {
            "content": "Anaphylaxie-Therapie (ESA/EAACI 2021): Leitsymptome: Urtikaria, Angioödem, Bronchospasmus, Hypotonie, Übelkeit/Erbrechen. Sofort: 1. Adrenalin IM 0,3–0,5 mg (lat. Oberschenkel, wdh. nach 5–15 min), 2. Trendelenburg-Lage, 3. O2, 4. iv-Zugang + kristalloide Infusion 20 ml/kg Bolus, 5. H1-Blocker (Dimetinden 0,1 mg/kg) + H2-Blocker (Ranitidin) + Prednisolon 1 mg/kg iv (wirkt verzögert). Bei Bronchospasmus Salbutamol inhal. Monitoring ≥6h (biphasischer Verlauf).",
            "metadata": {"source": "EAACI Anaphylaxis Guidelines", "code": "T78.2", "category": "Notfallmedizin", "language": "de"},
        },
        {
            "content": "Betablocker (z. B. Metoprolol, Bisoprolol): Indikationen: Hypertonie, KHK, Herzinsuffizienz (NYHA II–IV), Vorhofflimmern (Frequenzkontrolle), Migräneprophylaxe, Hyperthyreose. KI: Asthma bronchiale (relativ bei kardioselektiven), AV-Block II/III, akute dekompensierte HI, schwere Bradykardie (<50/min), Hypotonie. NW: Bradykardie, Müdigkeit, erektile Dysfunktion, Bronchokonstriktion.",
            "metadata": {"source": "Pharma-Lexikon", "code": "C07", "category": "Pharmakologie", "language": "de"},
        },
        {
            "content": "ACE-Hemmer (Ramipril, Enalapril, Lisinopril): Mechanismus: Hemmung von Angiotensin-Converting-Enzyme → weniger Angiotensin II. Indikationen: Hypertonie, Herzinsuffizienz, Post-Myokardinfarkt, diabetische Nephropathie. NW: Reizhusten (~10%, durch Bradykinin), Angioödem, Hyperkaliämie, Nierenfunktion-Kontrolle (Kreatinin-Anstieg ≤30% akzeptabel). KI: Schwangerschaft (!), bilaterale Nierenarterienstenose, Z. n. Angioödem.",
            "metadata": {"source": "Pharma-Lexikon", "code": "C09A", "category": "Pharmakologie", "language": "de"},
        },
    ]
    now = datetime.now(timezone.utc).isoformat()
    ids = [f"seed_{i}" for i in range(len(seed_docs))]
    contents = [d["content"] for d in seed_docs]
    metadatas = [{**d["metadata"], "version": "1.0", "uploaded_at": now} for d in seed_docs]
    embeddings = _embed_texts(contents)
    _collection.add(ids=ids, documents=contents, metadatas=metadatas, embeddings=embeddings)
    logger.info(f"[RAG] Seeded {len(seed_docs)} medical KB documents")


# ───────────────────────── CHUNKER ─────────────────────────
def _chunk_text(text: str, chunk_size: Optional[int] = None, overlap: Optional[int] = None) -> List[str]:
    cs = chunk_size or RAG_CHUNK_SIZE
    ov = overlap or RAG_CHUNK_OVERLAP
    words = text.split()
    if not words:
        return []
    chunks, i = [], 0
    while i < len(words):
        chunk = " ".join(words[i : i + cs])
        if chunk.strip():
            chunks.append(chunk)
        i += cs - ov
    return chunks


def _unified_chunks_from_text(
    *,
    source: str,
    content_chunks: list[str],
    category: str,
    language: str,
    version: str,
    filename: str = "",
) -> list[dict]:
    document_id = "med_" + hashlib.sha256(f"{source}|{version}|{filename}".encode("utf-8")).hexdigest()[:24]
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "document_id": document_id,
            "chunk_index": i,
            "text": text,
            "source_type": "medical",
            "document_type": "medical_kb",
            "source": source,
            "filename": filename or source,
            "category": category,
            "chunk_title": source,
            "word_count": len(text.split()),
            "updated_at": now,
            "metadata": {
                "language": language,
                "version": version,
                "source": source,
                "category": category,
                "filename": filename,
            },
        }
        for i, text in enumerate(content_chunks)
    ]


# ───────────────────────── LLM CALL ─────────────────────────
async def _llm_call(system: str, user: str, model: str = DEFAULT_LLM_MODEL, max_tokens: int = 1500) -> str:
    if not OPENROUTER_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY nicht konfiguriert")
    import httpx
    async with httpx.AsyncClient(timeout=90.0) as client:
        r = await client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://mcq-medical-prep.academy",
                "X-Title": "PrepAcademy RAG",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
        )
        data = r.json()
        if "choices" not in data or not data["choices"]:
            err = data.get("error", {}).get("message", str(data)[:200])
            logger.error(f"[RAG] OpenRouter error: {err}")
            raise HTTPException(status_code=503, detail=f"LLM-Fehler: {err}")
        return data["choices"][0]["message"]["content"]


async def _llm_call_with_fallback(system: str, user: str, model: str = DEFAULT_LLM_MODEL, max_tokens: int = 1500) -> Tuple[Optional[str], bool]:
    try:
        return await _llm_call(system, user, model=model, max_tokens=max_tokens), True
    except HTTPException as e:
        if "503" in str(e.status_code):
            logger.warning("[RAG] LLM unavailable, retrying once after 2s...")
            await asyncio.sleep(2)
            try:
                return await _llm_call(system, user, model=model, max_tokens=max_tokens), True
            except Exception:
                pass
        return None, False
    except Exception as e:
        logger.warning("[RAG] LLM call failed: %s", e)
        await asyncio.sleep(2)
        try:
            return await _llm_call(system, user, model=model, max_tokens=max_tokens), True
        except Exception:
            pass
        return None, False


# ───────────────────────── LANGUAGE PROMPTS ─────────────────────────
LANG_INSTRUCT = {
    "de": "Antworte auf Deutsch. Nutze medizinische Fachsprache präzise.",
    "en": "Answer in English using precise medical terminology.",
    "ar": "أجب باللغة العربية مع ذكر المصطلحات الطبية الألمانية بين قوسين.",
    "ru": "Отвечайте на русском языке с указанием немецких терминов в скобках.",
    "uk": "Відповідайте українською з німецькою термінологією у дужках.",
}


def _build_rag_prompt(query: str, sources: List[Dict], language: str = "de",
                      conversation_history: Optional[List[Dict]] = None) -> str:
    lang = LANG_INSTRUCT.get(language, LANG_INSTRUCT["de"])
    sources_block = "\n\n".join(
        [
            f"[{i+1}] ({s['metadata'].get('source', 'Unbekannt')} — {s['metadata'].get('code', '')})\n{s['content']}"
            for i, s in enumerate(sources)
        ]
    )
    history_block = ""
    if conversation_history:
        turns = []
        for turn in conversation_history[-6:]:
            role = turn.get("role", "user")
            text = turn.get("content", "")
            prefix = "Frage" if role == "user" else "Antwort"
            turns.append(f"{prefix}: {text}")
        if turns:
            history_block = "Bisheriger Verlauf:\n" + "\n".join(turns) + "\n\n"
    return f"""{lang}

Beantworte die folgende medizinische Frage AUSSCHLIESSLICH auf Basis der untenstehenden, nummerierten Quellen.
Zitiere jede verwendete Quelle am Satzende mit [1], [2], usw.
Wenn die Quellen keine Antwort enthalten, sage das ehrlich.

{history_block}FRAGE:
{query}

QUELLEN:
{sources_block}

Antwort (mit [Nummer]-Zitaten):"""


# ═════════════════════════ CONFIDENCE SCORE ═════════════════════════
def _compute_confidence(sources: List[Dict], citation_coverage: float) -> Tuple[float, bool]:
    if not sources:
        return 0.0, True
    rerank_scores = [s.get("rerank_score") for s in sources if s.get("rerank_score") is not None]
    if rerank_scores:
        avg_rerank = sum(rerank_scores) / len(rerank_scores)
        rerank_score = max(0.0, min(1.0, (avg_rerank + 1) / 2))
    else:
        chroma_scores = [s.get("score", 0) for s in sources if s.get("score") is not None]
        rerank_score = sum(chroma_scores) / max(len(chroma_scores), 1) if chroma_scores else 0.3
    confidence = 0.6 * rerank_score + 0.4 * citation_coverage
    confidence = max(0.0, min(1.0, confidence))
    low_conf = confidence < 0.5
    return round(confidence, 4), low_conf


# ═════════════════════════ ENDPOINTS ═════════════════════════

class QueryRequest(BaseModel):
    query: str
    language: str = "de"
    top_k: int = 5
    model: str = DEFAULT_LLM_MODEL
    filter_category: Optional[str] = None
    session_id: Optional[str] = None


class IngestTextRequest(BaseModel):
    content: str
    source: str = "user_upload"
    category: str = "Allgemein"
    language: str = "de"
    force: bool = False


class KBFeedbackRequest(BaseModel):
    source_name: str
    feedback_type: str
    comment: str = ""
    suggested_correction: str = ""


class AnalyzerRAGRequest(BaseModel):
    finding: str
    patient_context: str = ""
    language: str = "de"
    top_k: int = 4


# ───────────────────────── SESSION / CONVERSATION ─────────────────────────
async def _get_session_history(session_id: str) -> Optional[List[Dict]]:
    r = _get_redis()
    if not r or not session_id:
        return None
    try:
        raw = await r.get(f"rag_session:{session_id}")
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


async def _save_session_history(session_id: str, history: List[Dict]) -> None:
    r = _get_redis()
    if not r:
        return
    try:
        history = history[-10:]
        await r.setex(f"rag_session:{session_id}", 7200, json.dumps(history))
    except Exception:
        pass


# ───────────────────────── STATUS ─────────────────────────

@router.get("/status")
async def rag_status():
    """Check unified RAG status. Legacy Chroma is reported separately."""
    try:
        legacy_count = _collection.count() if _collection else 0
    except Exception:
        legacy_count = 0
    unified_count = count_unified()
    return {
        "ready": unified_count > 0 or _init_state["ready"],
        "active_vector_store": "qdrant",
        "model": "openai/text-embedding-3-small",
        "error": _init_state["error"],
        "kb_document_count": unified_count,
        "unified_document_count": unified_count,
        "legacy_chroma_document_count": legacy_count,
        "legacy_chroma_ready": _init_state["ready"],
        "legacy_chroma_model": _init_state["model"],
        "chunk_size": RAG_CHUNK_SIZE,
        "chunk_overlap": RAG_CHUNK_OVERLAP,
        "cache_hits": _cache_hits,
        "cache_misses": _cache_misses,
        "redis_connected": _redis_available,
    }


@router.get("/ingestion/status")
async def rag_ingestion_status(user: dict = Depends(get_admin_user)):
    """Admin: summarize background RAG ingestion jobs."""
    return {
        "queue": await status_summary(),
        "recent_jobs": await list_jobs(limit=10),
    }


@router.get("/ingestion/jobs/{job_id}")
async def rag_ingestion_job(job_id: str, user: dict = Depends(get_admin_user)):
    """Admin: fetch one background ingestion job."""
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return job


@router.get("/ingestion/jobs")
async def rag_ingestion_jobs(limit: int = 20, user: dict = Depends(get_admin_user)):
    """Admin: list recent background ingestion jobs."""
    return {"jobs": await list_jobs(limit=limit)}


# SOURCE VERSIONING ─────────────────────────

async def _get_source_version(source_name: str) -> str:
    meta = _collection.get(where={"source": source_name}, include=["metadatas"])
    metas = meta.get("metadatas", []) or []
    versions = set()
    for m in metas:
        v = m.get("version", "1.0")
        versions.add(v)
    return max(versions) if versions else "1.0"


async def _resolve_source_name(source_name: str, force: bool = False) -> str:
    existing = _collection.get(where={"source": source_name}, include=["metadatas"])
    existing_metas = existing.get("metadatas", []) or []
    if not existing_metas:
        return source_name
    if force:
        current_ver = await _get_source_version(source_name)
        parts = current_ver.split(".")
        major = int(parts[0]) if parts[0].isdigit() else 1
        minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        new_ver = f"{major}.{minor + 1}"
        logger.info("[RAG] Auto-versioning source '%s': %s -> %s", source_name, current_ver, new_ver)
        return source_name
    return source_name


# ───────────────────────── QUERY ─────────────────────────

@router.post("/query")
@limiter.limit(_RATE_LIMIT)
async def rag_query(request: Request, req: QueryRequest, user: dict = Depends(get_current_user)):
    """RAG answer: retrieve top-K relevant docs + DeepSeek-V3 answer with citations."""
    sanitized = _sanitize_query(req.query)
    if not sanitized:
        raise HTTPException(status_code=400, detail="Leere Anfrage")

    retrieval = await unified_retrieve(RetrievalRequest(
        query=sanitized,
        top_k=req.top_k,
        filters={"category": req.filter_category} if req.filter_category else None,
        use_hybrid=True,
        use_reranker=True,
    ))
    source_records = retrieval["sources"]
    if not source_records:
        return {"answer": "Keine relevanten Quellen gefunden.", "sources": [], "model": req.model,
                "session_id": req.session_id}

    sources = [
        {
            "content": s.get("excerpt", ""),
            "metadata": {
                "source": s.get("source", "Unbekannt"),
                "code": "",
                "category": s.get("category", ""),
                "note_title": s.get("note_title", ""),
                "vault_path": s.get("vault_path", ""),
                "source_type": s.get("source_type", ""),
            },
            "score": s.get("retrieval_score") or s.get("score"),
            "rerank_score": s.get("score") if isinstance(s.get("score"), (int, float)) else None,
        }
        for s in source_records
    ]

    session_history = None
    if req.session_id:
        session_history = await _get_session_history(req.session_id)

    prompt = _build_rag_prompt(sanitized, sources, req.language, session_history)
    system = "Du bist ein präziser medizinischer Assistent für Prüfungsvorbereitung. Zitiere IMMER die Quellen mit [N]."

    answer_text, llm_ok = await _llm_call_with_fallback(system, prompt, model=req.model)

    query_id = str(uuid.uuid4())
    answer_reply = answer_text if llm_ok else None
    await db.rag_queries.insert_one({
        "id": query_id,
        "user_id": user["id"],
        "query": sanitized,
        "language": req.language,
        "model": req.model,
        "source_count": len(sources),
        "sources": source_records,
        "answer_reply": answer_reply,
        "llm_generated": llm_ok,
        "retrieval": retrieval.get("orchestrator", {}),
        "retrieval_latency_ms": retrieval.get("latency_ms"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    if not llm_ok or not answer_text:
        return {
            "answer": None,
            "llm_unavailable": True,
            "sources": source_records,
            "model": req.model,
            "language": req.language,
            "query_id": query_id,
            "session_id": req.session_id,
            "note": "LLM temporär nicht verfügbar — Quellen werden direkt angezeigt.",
        }

    clean_answer, hallucination, citation_coverage = _check_citations(answer_text, len(sources))
    confidence, low_conf_warning = _compute_confidence(sources, citation_coverage)

    if req.session_id:
        new_history = (session_history or []) + [
            {"role": "user", "content": sanitized},
            {"role": "assistant", "content": clean_answer},
        ]
        await _save_session_history(req.session_id, new_history)

    response = {
        "answer": clean_answer,
        "hallucination_detected": hallucination,
        "sources": source_records,
        "model": req.model,
        "language": req.language,
        "query_id": query_id,
        "session_id": req.session_id or "",
        "confidence_score": confidence,
        "low_confidence_warning": low_conf_warning,
        "citation_coverage": round(citation_coverage, 4),
        "retrieval": retrieval.get("orchestrator", {}),
        "retrieval_latency_ms": retrieval.get("latency_ms"),
    }
    return response


# ───────────────────────── QUERY EXPORT PDF ─────────────────────────

@router.post("/export-pdf/{query_id}")
async def export_rag_pdf(query_id: str, user: dict = Depends(get_current_user)):
    """Generate a PDF of a previous RAG query result."""
    from fastapi.responses import StreamingResponse
    from fpdf import FPDF

    query_doc = await db.rag_queries.find_one({"id": query_id, "user_id": user["id"]}, {"_id": 0})
    if not query_doc:
        raise HTTPException(status_code=404, detail="Query-ID nicht gefunden oder nicht berechtigt")
    query_text = query_doc.get("query", "")
    sources = query_doc.get("sources", [])

    font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")
    font_regular = os.path.join(font_dir, "DejaVuSans.ttf")
    font_bold = os.path.join(font_dir, "DejaVuSans-Bold.ttf")

    pdf = FPDF()
    pdf.add_page()
    if os.path.exists(font_regular):
        pdf.add_font("DejaVu", "", font_regular)
        pdf.set_font("DejaVu", size=10)
        has_bold = os.path.exists(font_bold)
        if has_bold:
            pdf.add_font("DejaVu", "B", font_bold)
    else:
        pdf.set_font("Helvetica", size=10)
        has_bold = True

    def _font(bold=False, size=10):
        if os.path.exists(font_regular):
            pdf.set_font("DejaVu", "B" if (bold and has_bold) else "", size)
        else:
            pdf.set_font("Helvetica", "B" if bold else "", size)

    _font(bold=True, size=16)
    pdf.set_text_color(201, 168, 76)
    pdf.cell(0, 10, "Prep Academy - Medical RAG", ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    _font(size=8)
    pdf.cell(0, 5, f"Query-ID: {query_id}  |  {query_doc.get('created_at','')[:19]}  |  Sprache: {query_doc.get('language','de')}", ln=True, align="C")
    pdf.ln(6)

    _font(bold=True, size=12)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 8, "Frage:", ln=True)
    _font(size=10)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 5, query_text)
    pdf.ln(4)

    if query_doc.get("llm_generated", True) and query_doc.get("answer_reply"):
        _font(bold=True, size=12)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(0, 8, "Antwort:", ln=True)
        _font(size=10)
        pdf.set_text_color(0, 0, 0)
        answer_text = query_doc.get("answer_reply", "")
        for line in answer_text.split("\n"):
            if line.strip():
                pdf.multi_cell(0, 5, line)
            else:
                pdf.ln(2)
        pdf.ln(4)

    _font(bold=True, size=11)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 8, "Quellen:", ln=True)
    _font(size=9)
    pdf.set_text_color(0, 0, 0)
    for s in sources:
        src_name = s.get("source", "Unbekannt")
        code = s.get("code", "")
        excerpt = s.get("excerpt", "")[:400]
        score = s.get("score", "")
        label = f"[{s.get('index','?')}] {src_name}"
        if code:
            label += f" ({code})"
        if score:
            label += f" — Score: {score:.2f}" if isinstance(score, (int, float)) else f" — Score: {score}"
        _font(bold=True, size=9)
        pdf.multi_cell(0, 5, label, new_x="LMARGIN", new_y="NEXT")
        _font(size=9)
        pdf.multi_cell(0, 5, excerpt[:400], new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    pdf.ln(4)
    _font(size=7)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 4, f"Erstellt: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} | KB-Version: v1", ln=True)

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    filename = f"rag_answer_{query_id[:8]}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ───────────────────────── ANALYZER ─────────────────────────

@router.post("/analyzer")
@limiter.limit(_RATE_LIMIT)
async def rag_analyzer(request: Request, req: AnalyzerRAGRequest, user: dict = Depends(get_current_user)):
    """Combine an X-ray AI finding with Medscape-style protocol lookup."""
    combined_query = f"{req.finding}\n{req.patient_context}".strip()
    retrieval = await unified_retrieve(RetrievalRequest(
        query=combined_query,
        top_k=req.top_k,
        use_hybrid=True,
        use_reranker=True,
    ))
    sources = [
        {
            "content": s.get("excerpt", ""),
            "metadata": {
                "source": s.get("source", ""),
                "code": "",
                "category": s.get("category", ""),
                "note_title": s.get("note_title", ""),
                "vault_path": s.get("vault_path", ""),
            },
            "score": s.get("retrieval_score") or s.get("score"),
            "rerank_score": s.get("score") if isinstance(s.get("score"), (int, float)) else None,
        }
        for s in retrieval.get("sources", [])
    ]

    system = "Du bist ein klinischer Entscheidungsunterstützungsassistent. Kombiniere Befunde mit Leitlinien. Zitiere IMMER mit [N]."
    user_prompt = f"""{LANG_INSTRUCT.get(req.language, LANG_INSTRUCT['de'])}

BEFUND (aus Bildanalyse):
{req.finding}

PATIENTENKONTEXT:
{req.patient_context or '(kein zusätzlicher Kontext)'}

LEITLINIEN:
{chr(10).join([f'[{i+1}] {s["metadata"].get("source","")}: {s["content"][:500]}' for i, s in enumerate(sources)])}

Erstelle:
1) Verdachtsdiagnose (mit ICD-10)
2) Weiterführende Diagnostik
3) Therapieempfehlung (mit Leitlinien-Zitaten [N])
4) Warnzeichen / Red Flags
5) Monitoring"""

    answer_text, llm_ok = await _llm_call_with_fallback(system, user_prompt, max_tokens=2000)
    if answer_text:
        clean_answer, hallucination, _ = _check_citations(answer_text, len(sources))
    else:
        clean_answer = None
        hallucination = False

    return {
        "clinical_report": clean_answer or "LLM temporär nicht verfügbar.",
        "hallucination_detected": hallucination,
        "sources": [
            {
                "index": i + 1,
                "source": s["metadata"].get("source", ""),
                "code": s["metadata"].get("code", ""),
                "category": s["metadata"].get("category", ""),
                "excerpt": s["content"][:250],
                "score": s.get("rerank_score") or s.get("score"),
            }
            for i, s in enumerate(sources)
        ],
        "language": req.language,
    }


# ───────────────────────── INGEST TEXT ─────────────────────────

@router.post("/ingest-text")
async def ingest_text(req: IngestTextRequest, user: dict = Depends(get_admin_user)):
    """Admin: enqueue a text document ingestion job."""
    chunks = _chunk_text(req.content)
    if not chunks:
        raise HTTPException(status_code=400, detail="Inhalt zu kurz")

    now = datetime.now(timezone.utc).isoformat()
    version = now if req.force else "1.0"
    job = await create_job(
        job_type="rag_ingest_text",
        source_type="medical",
        requested_by=user.get("id", ""),
        payload={
            "source": req.source,
            "category": req.category,
            "language": req.language,
            "version": version,
            "chunk_count": len(chunks),
        },
    )

    async def worker():
        await update_job_progress(job["id"], total=len(chunks), processed=0, message="Embedding text chunks")
        unified_chunks = _unified_chunks_from_text(
            source=req.source,
            content_chunks=chunks,
            category=req.category,
            language=req.language,
            version=version,
        )
        added = await upsert_unified_chunks(unified_chunks)
        failed = max(0, len(chunks) - added)
        await update_job_progress(job["id"], total=len(chunks), processed=added, failed=failed)
        return {
            "source": req.source,
            "version": version,
            "added_chunks": added,
            "failed_chunks_count": failed,
            "total_kb_docs": count_unified(),
        }

    start_job(job["id"], worker)
    return {
        "accepted": True,
        "job_id": job["id"],
        "status": job["status"],
        "source": req.source,
        "queued_chunks": len(chunks),
    }


# ───────────────────────── INGEST PDF ─────────────────────────

def _validate_pdf(content: bytes) -> Tuple[bool, str, str]:
    """Validate PDF integrity and extractability. Returns (valid, error_msg, text)."""
    if not content or len(content) < 20:
        return False, "Leere oder zu kurze Datei", ""
    if content[:5] != b"%PDF-":
        return False, "Datei ist kein gültiges PDF (fehlende PDF-Signatur)", ""
    try:
        import fitz
        doc = fitz.open(stream=content, filetype="pdf")
        if len(doc) == 0:
            doc.close()
            return False, "PDF enthält keine Seiten", ""
        text_parts = []
        for page in doc:
            t = page.get_text() or ""
            text_parts.append(t)
        doc.close()
        text = "\n".join(text_parts)
        if not text.strip():
            return False, "PDF enthält keinen extrahierbaren Text (möglicherweise ein gescanntes Dokument ohne OCR)", ""
        if len(text.strip()) < 100:
            return False, f"PDF enthält nur {len(text.strip())} Zeichen extrahierbaren Text — zu wenig für eine sinnvolle Verarbeitung (min. 100)", ""
        return True, "", text
    except Exception as e:
        err_msg = str(e)
        if "encrypted" in err_msg.lower() or "password" in err_msg.lower():
            return False, "PDF ist verschlüsselt und kann nicht gelesen werden", ""
        return False, f"PDF konnte nicht gelesen werden: {err_msg}", ""


@router.post("/ingest-pdf")
async def ingest_pdf(
    file: UploadFile = File(...),
    source: str = Form(...),
    category: str = Form("Allgemein"),
    language: str = Form("de"),
    force: bool = Form(False),
    user: dict = Depends(get_admin_user),
):
    """Admin: upload a PDF and enqueue ingestion into the unified KB."""
    content = await file.read()
    valid, error_msg, text = _validate_pdf(content)
    if not valid:
        raise HTTPException(status_code=400, detail=error_msg)

    chunks = _chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=400, detail="PDF text too short after chunking")

    now = datetime.now(timezone.utc).isoformat()
    version = now if force else "1.0"
    job = await create_job(
        job_type="rag_ingest_pdf",
        source_type="medical",
        requested_by=user.get("id", ""),
        payload={
            "source": source,
            "category": category,
            "language": language,
            "filename": file.filename,
            "version": version,
            "chunk_count": len(chunks),
            "total_chars": len(text),
        },
    )

    async def worker():
        await update_job_progress(job["id"], total=len(chunks), processed=0, message="Embedding PDF chunks")
        unified_chunks = _unified_chunks_from_text(
            source=source,
            content_chunks=chunks,
            category=category,
            language=language,
            version=version,
            filename=file.filename or "",
        )
        added = await upsert_unified_chunks(unified_chunks)
        failed = max(0, len(chunks) - added)
        await update_job_progress(job["id"], total=len(chunks), processed=added, failed=failed)
        return {
            "filename": file.filename,
            "source": source,
            "version": version,
            "total_chars": len(text),
            "added_chunks": added,
            "failed_chunks_count": failed,
            "total_kb_docs": count_unified(),
        }

    start_job(job["id"], worker)

    return {
        "accepted": True,
        "job_id": job["id"],
        "status": job["status"],
        "filename": file.filename,
        "total_chars": len(text),
        "queued_chunks": len(chunks),
        "version": version,
    }


# ───────────────────────── SOURCES ─────────────────────────

@router.get("/sources")
async def list_sources(user: dict = Depends(get_current_user)):
    """List all unique sources currently in the unified Qdrant KB."""
    sources = list_unified_sources()
    return {"sources": sources, "total_docs": count_unified()}


@router.post("/obsidian/sync")
async def obsidian_sync(user: dict = Depends(get_admin_user)):
    """Admin: enqueue an incremental Obsidian vault sync."""
    job = await create_job(
        job_type="obsidian_sync",
        source_type="obsidian",
        requested_by=user.get("id", ""),
        payload={"force": False},
    )

    async def worker():
        await update_job_progress(job["id"], message="Syncing Obsidian vault")
        result = await sync_obsidian_vault(force=False)
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "Obsidian sync failed"))
        await update_job_progress(
            job["id"],
            total=result.get("notes_scanned", 0),
            processed=result.get("notes_indexed", 0) + result.get("notes_skipped", 0),
            failed=0,
        )
        return result

    start_job(job["id"], worker)
    return {"accepted": True, "job_id": job["id"], "status": job["status"]}


@router.get("/obsidian/status")
async def obsidian_status(user: dict = Depends(get_admin_user)):
    """Admin: return Obsidian vault indexing status."""
    return await get_obsidian_status()


@router.post("/obsidian/reindex")
async def obsidian_reindex(user: dict = Depends(get_admin_user)):
    """Admin: enqueue a full Obsidian vault reindex."""
    job = await create_job(
        job_type="obsidian_reindex",
        source_type="obsidian",
        requested_by=user.get("id", ""),
        payload={"force": True},
    )

    async def worker():
        await update_job_progress(job["id"], message="Reindexing Obsidian vault")
        result = await reindex_obsidian_vault()
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "Obsidian reindex failed"))
        await update_job_progress(
            job["id"],
            total=result.get("notes_scanned", 0),
            processed=result.get("notes_indexed", 0),
            failed=0,
        )
        return result

    start_job(job["id"], worker)
    return {"accepted": True, "job_id": job["id"], "status": job["status"]}


@router.get("/obsidian/search")
async def obsidian_search(q: str, limit: int = 5, user: dict = Depends(get_current_user)):
    """Search only Obsidian-backed RAG chunks."""
    return {"results": await search_obsidian(q, limit=min(max(limit, 1), 20))}


@router.get("/source/{source_name}/versions")
async def list_source_versions(source_name: str, user: dict = Depends(get_current_user)):
    """List all versions of a given source from unified Qdrant payloads."""
    versions = list_unified_source_versions(source_name)
    return {"source": source_name, "versions": versions, "total_chunks": sum(v.get("chunks", 0) for v in versions)}


@router.delete("/source/{source_name}")
async def delete_source(source_name: str, version: Optional[str] = None, user: dict = Depends(get_admin_user)):
    """Admin: delete unified Qdrant chunks for a source. Optionally filter by version."""
    filters: Dict[str, Any] = {"source": source_name}
    if version:
        filters["version"] = version
    deleted = delete_unified(filters)
    return {
        "deleted_source": source_name,
        "version": version or "all",
        "deleted_chunks": deleted,
        "remaining_docs": count_unified(),
    }


# ═══════════════════════════════════════════════════════════════
# KB FEEDBACK LOOP
# ═══════════════════════════════════════════════════════════════

@router.post("/feedback")
async def submit_kb_feedback(req: KBFeedbackRequest, user: dict = Depends(get_current_user)):
    """Submit user feedback on a KB source entry."""
    if req.feedback_type not in ("correct", "incorrect", "outdated", "irrelevant", "suggestion"):
        raise HTTPException(status_code=400, detail="Invalid feedback_type.")
    entry = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "source_name": req.source_name,
        "feedback_type": req.feedback_type,
        "comment": req.comment[:500],
        "suggested_correction": req.suggested_correction[:2000],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db.kb_feedback.insert_one(entry)
    except Exception as e:
        logger.error(f"[KB] Failed to save feedback: {e}")
        raise HTTPException(status_code=500, detail="Feedback konnte nicht gespeichert werden")
    return {"success": True, "feedback_id": entry["id"]}


@router.get("/feedback")
async def list_kb_feedback(user: dict = Depends(get_admin_user), limit: int = 50):
    """Admin: list all submitted KB feedback entries."""
    items = await db.kb_feedback.find({}, {"_id": 0}).sort("created_at", -1).to_list(min(limit, 200))
    return {"items": items, "count": len(items)}


@router.get("/feedback/stats")
async def kb_feedback_stats(user: dict = Depends(get_admin_user)):
    """Admin: aggregate KB feedback stats by source and type."""
    pipeline = [
        {"$group": {"_id": {"source": "$source_name", "type": "$feedback_type"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    try:
        results = await db.kb_feedback.aggregate(pipeline).to_list(200)
    except Exception:
        return {"stats": [], "total": 0}
    stats = []
    total = 0
    for r in results:
        stats.append({"source": r["_id"]["source"], "feedback_type": r["_id"]["type"], "count": r["count"]})
        total += r["count"]
    return {"stats": stats, "total": total}
