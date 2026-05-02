"""
Medical RAG (Retrieval-Augmented Generation) System
====================================================
- Vector Store: ChromaDB (persistent, local, free)
- Embeddings: BGE-M3 (multilingual, local, free) via sentence-transformers
  with graceful fallback to a lighter multilingual model
- LLM: DeepSeek-V3 via OpenRouter (cheap, high-quality)
- Knowledge Base: ICD-10 (DE), WHO Guidelines, RKI Protocols (seed)

The models are lazy-loaded on first request to keep the server's startup fast
and the health-check responsive.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import uuid
import asyncio
import json
from datetime import datetime, timezone

from database import db, logger
from auth import get_current_user, get_admin_user

router = APIRouter(prefix="/api/rag", tags=["rag"])

# ───────────────────────── CONFIG ─────────────────────────
CHROMA_DIR = os.environ.get("CHROMA_DIR", "/app/backend/.chroma")
COLLECTION_NAME = "medical_kb"
# Primary embedding model (multilingual, supports DE + AR + EN + RU)
PRIMARY_EMBED_MODEL = os.environ.get("RAG_EMBED_MODEL", "BAAI/bge-m3")
# Fallback if BGE-M3 fails to load (disk/memory): lighter multilingual
FALLBACK_EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_LLM_MODEL = "deepseek/deepseek-chat-v3.1"

# ───────────────────────── LAZY SINGLETONS ─────────────────────────
_embed_model = None
_chroma_client = None
_collection = None
_init_lock = asyncio.Lock()
_init_state: Dict[str, Any] = {"ready": False, "error": "", "model": ""}


def _load_embed_model_sync():
    """Load the sentence-transformer model (blocking, run in executor)."""
    from sentence_transformers import SentenceTransformer
    try:
        logger.info(f"[RAG] Loading primary embedding model: {PRIMARY_EMBED_MODEL}")
        return SentenceTransformer(PRIMARY_EMBED_MODEL, device="cpu"), PRIMARY_EMBED_MODEL
    except Exception as e:
        logger.warning(f"[RAG] Primary model failed ({e}), falling back to {FALLBACK_EMBED_MODEL}")
        return SentenceTransformer(FALLBACK_EMBED_MODEL, device="cpu"), FALLBACK_EMBED_MODEL


async def _ensure_initialized():
    """Lazy-init embedding model, Chroma collection, and seed KB once."""
    global _embed_model, _chroma_client, _collection
    if _init_state["ready"]:
        return
    async with _init_lock:
        if _init_state["ready"]:
            return
        try:
            # 1) Embedding model (in executor — heavy I/O and CPU)
            loop = asyncio.get_event_loop()
            _embed_model, model_name = await loop.run_in_executor(None, _load_embed_model_sync)
            _init_state["model"] = model_name

            # 2) ChromaDB persistent client
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

            # 3) Seed initial KB if empty
            if _collection.count() == 0:
                await loop.run_in_executor(None, _seed_initial_kb)

            _init_state["ready"] = True
            _init_state["error"] = ""
            logger.info(f"[RAG] Ready. Model={model_name}, KB docs={_collection.count()}")
        except Exception as e:
            _init_state["error"] = str(e)
            logger.error(f"[RAG] Init failed: {e}")
            raise HTTPException(status_code=503, detail=f"RAG-System nicht bereit: {e}")


def _embed_texts(texts: List[str]) -> List[List[float]]:
    """Synchronous embedding — call via executor from async code."""
    vecs = _embed_model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    # sentence-transformers returns numpy array
    return vecs.tolist() if hasattr(vecs, "tolist") else [list(v) for v in vecs]


# ───────────────────────── SEED KNOWLEDGE BASE ─────────────────────────
def _seed_initial_kb():
    """Seed the collection with medically verified content (German primary).
    Sources: ICD-10-GM (public domain), WHO treatment guidelines (open), RKI recommendations (public)."""
    seed_docs = [
        # ═══ ICD-10-GM (deutsch, gekürzt) ═══
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
        # ═══ WHO / Notfallprotokolle (englisch referenziert, deutscher Inhalt) ═══
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
        # ═══ Pharmakologie-Basics ═══
        {
            "content": "Betablocker (z. B. Metoprolol, Bisoprolol): Indikationen: Hypertonie, KHK, Herzinsuffizienz (NYHA II–IV), Vorhofflimmern (Frequenzkontrolle), Migräneprophylaxe, Hyperthyreose. KI: Asthma bronchiale (relativ bei kardioselektiven), AV-Block II/III, akute dekompensierte HI, schwere Bradykardie (<50/min), Hypotonie. NW: Bradykardie, Müdigkeit, erektile Dysfunktion, Bronchokonstriktion.",
            "metadata": {"source": "Pharma-Lexikon", "code": "C07", "category": "Pharmakologie", "language": "de"},
        },
        {
            "content": "ACE-Hemmer (Ramipril, Enalapril, Lisinopril): Mechanismus: Hemmung von Angiotensin-Converting-Enzyme → weniger Angiotensin II. Indikationen: Hypertonie, Herzinsuffizienz, Post-Myokardinfarkt, diabetische Nephropathie. NW: Reizhusten (~10%, durch Bradykinin), Angioödem, Hyperkaliämie, Nierenfunktion-Kontrolle (Kreatinin-Anstieg ≤30% akzeptabel). KI: Schwangerschaft (!), bilaterale Nierenarterienstenose, Z. n. Angioödem.",
            "metadata": {"source": "Pharma-Lexikon", "code": "C09A", "category": "Pharmakologie", "language": "de"},
        },
    ]

    ids = [f"seed_{i}" for i in range(len(seed_docs))]
    contents = [d["content"] for d in seed_docs]
    metadatas = [d["metadata"] for d in seed_docs]
    embeddings = _embed_texts(contents)

    _collection.add(ids=ids, documents=contents, metadatas=metadatas, embeddings=embeddings)
    logger.info(f"[RAG] Seeded {len(seed_docs)} medical KB documents")


# ───────────────────────── CHUNKER ─────────────────────────
def _chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> List[str]:
    """Simple word-based chunker with overlap."""
    words = text.split()
    if not words:
        return []
    chunks, i = [], 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


# ───────────────────────── LLM CALL ─────────────────────────
async def _llm_call(system: str, user: str, model: str = DEFAULT_LLM_MODEL, max_tokens: int = 1500) -> str:
    """Call DeepSeek-V3 (or configured model) via OpenRouter."""
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


# ───────────────────────── LANGUAGE PROMPTS ─────────────────────────
LANG_INSTRUCT = {
    "de": "Antworte auf Deutsch. Nutze medizinische Fachsprache präzise.",
    "en": "Answer in English using precise medical terminology.",
    "ar": "أجب باللغة العربية مع ذكر المصطلحات الطبية الألمانية بين قوسين.",
    "ru": "Отвечайте на русском языке с указанием немецких терминов в скобках.",
    "uk": "Відповідайте українською з німецькою термінологією у дужках.",
}


def _build_rag_prompt(query: str, sources: List[Dict], language: str = "de") -> str:
    """Build the user prompt with numbered sources."""
    lang = LANG_INSTRUCT.get(language, LANG_INSTRUCT["de"])
    sources_block = "\n\n".join(
        [
            f"[{i+1}] ({s['metadata'].get('source', 'Unbekannt')} — {s['metadata'].get('code', '')})\n{s['content']}"
            for i, s in enumerate(sources)
        ]
    )
    return f"""{lang}

Beantworte die folgende medizinische Frage AUSSCHLIESSLICH auf Basis der untenstehenden, nummerierten Quellen.
Zitiere jede verwendete Quelle am Satzende mit [1], [2], usw.
Wenn die Quellen keine Antwort enthalten, sage das ehrlich.

FRAGE:
{query}

QUELLEN:
{sources_block}

Antwort (mit [Nummer]-Zitaten):"""


# ═════════════════════════ ENDPOINTS ═════════════════════════

class QueryRequest(BaseModel):
    query: str
    language: str = "de"
    top_k: int = 5
    model: str = DEFAULT_LLM_MODEL
    filter_category: Optional[str] = None


class IngestTextRequest(BaseModel):
    content: str
    source: str = "user_upload"
    category: str = "Allgemein"
    language: str = "de"


class AnalyzerRAGRequest(BaseModel):
    finding: str  # AI-generated X-ray/image finding
    patient_context: str = ""
    language: str = "de"
    top_k: int = 4


@router.get("/status")
async def rag_status():
    """Check if RAG is initialized (public — does NOT trigger init)."""
    try:
        count = _collection.count() if _collection else 0
    except Exception:
        count = 0
    return {
        "ready": _init_state["ready"],
        "model": _init_state["model"],
        "error": _init_state["error"],
        "kb_document_count": count,
    }


@router.post("/query")
async def rag_query(req: QueryRequest, user: dict = Depends(get_current_user)):
    """RAG answer: retrieve top-K relevant docs + DeepSeek-V3 answer with citations."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Leere Anfrage")

    await _ensure_initialized()

    loop = asyncio.get_event_loop()
    q_vec = await loop.run_in_executor(None, lambda: _embed_texts([req.query]))
    where = {"category": req.filter_category} if req.filter_category else None

    results = _collection.query(
        query_embeddings=q_vec,
        n_results=max(1, min(req.top_k, 10)),
        where=where,
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not docs:
        return {"answer": "Keine relevanten Quellen gefunden.", "sources": [], "model": req.model}

    sources = [
        {
            "content": doc,
            "metadata": meta,
            "score": round(1 - dist, 4) if dist is not None else None,
        }
        for doc, meta, dist in zip(docs, metas, distances)
    ]

    prompt = _build_rag_prompt(req.query, sources, req.language)
    system = "Du bist ein präziser medizinischer Assistent für Prüfungsvorbereitung. Zitiere IMMER die Quellen mit [N]."
    answer = await _llm_call(system, prompt, model=req.model)

    await db.rag_queries.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "query": req.query,
        "language": req.language,
        "model": req.model,
        "source_count": len(sources),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "answer": answer,
        "sources": [
            {
                "index": i + 1,
                "source": s["metadata"].get("source", "Unbekannt"),
                "code": s["metadata"].get("code", ""),
                "category": s["metadata"].get("category", ""),
                "excerpt": s["content"][:300] + ("..." if len(s["content"]) > 300 else ""),
                "score": s["score"],
            }
            for i, s in enumerate(sources)
        ],
        "model": req.model,
        "language": req.language,
    }


@router.post("/analyzer")
async def rag_analyzer(req: AnalyzerRAGRequest, user: dict = Depends(get_current_user)):
    """Combine an X-ray AI finding with Medscape-style protocol lookup."""
    await _ensure_initialized()

    combined_query = f"{req.finding}\n{req.patient_context}".strip()
    loop = asyncio.get_event_loop()
    q_vec = await loop.run_in_executor(None, lambda: _embed_texts([combined_query]))
    results = _collection.query(query_embeddings=q_vec, n_results=req.top_k)

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    sources = [{"content": d, "metadata": m} for d, m in zip(docs, metas)]

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

    answer = await _llm_call(system, user_prompt, max_tokens=2000)

    return {
        "clinical_report": answer,
        "sources": [
            {
                "index": i + 1,
                "source": s["metadata"].get("source", ""),
                "code": s["metadata"].get("code", ""),
                "category": s["metadata"].get("category", ""),
                "excerpt": s["content"][:250],
            }
            for i, s in enumerate(sources)
        ],
        "language": req.language,
    }


@router.post("/ingest-text")
async def ingest_text(req: IngestTextRequest, user: dict = Depends(get_admin_user)):
    """Admin: add a single text document to the KB."""
    await _ensure_initialized()

    chunks = _chunk_text(req.content)
    if not chunks:
        raise HTTPException(status_code=400, detail="Inhalt zu kurz")

    loop = asyncio.get_event_loop()
    embeddings = await loop.run_in_executor(None, lambda: _embed_texts(chunks))
    ids = [f"doc_{uuid.uuid4().hex[:12]}" for _ in chunks]
    metas = [
        {"source": req.source, "category": req.category, "language": req.language, "chunk": i}
        for i in range(len(chunks))
    ]
    _collection.add(ids=ids, documents=chunks, metadatas=metas, embeddings=embeddings)
    return {"added_chunks": len(chunks), "source": req.source, "total_kb_docs": _collection.count()}


@router.post("/ingest-pdf")
async def ingest_pdf(
    file: UploadFile = File(...),
    source: str = Form(...),
    category: str = Form("Allgemein"),
    language: str = Form("de"),
    user: dict = Depends(get_admin_user),
):
    """Admin: upload a PDF and ingest its text into the KB."""
    await _ensure_initialized()

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Leere Datei")

    text = ""
    try:
        import io
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception as e:
        logger.error(f"[RAG] PDF parse error: {e}")
        raise HTTPException(status_code=400, detail=f"PDF konnte nicht gelesen werden: {e}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="PDF enthält keinen extrahierbaren Text")

    chunks = _chunk_text(text)
    loop = asyncio.get_event_loop()
    embeddings = await loop.run_in_executor(None, lambda: _embed_texts(chunks))
    ids = [f"pdf_{uuid.uuid4().hex[:10]}_{i}" for i in range(len(chunks))]
    metas = [
        {"source": source, "category": category, "language": language, "filename": file.filename, "chunk": i}
        for i in range(len(chunks))
    ]
    _collection.add(ids=ids, documents=chunks, metadatas=metas, embeddings=embeddings)

    return {
        "filename": file.filename,
        "total_chars": len(text),
        "added_chunks": len(chunks),
        "total_kb_docs": _collection.count(),
    }


@router.get("/sources")
async def list_sources(user: dict = Depends(get_current_user)):
    """List all unique sources currently in the KB (requires auth)."""
    await _ensure_initialized()
    # Chroma doesn't support distinct directly; fetch metadata only
    all_items = _collection.get(include=["metadatas"])
    metas = all_items.get("metadatas", []) or []
    counts: Dict[str, Dict[str, Any]] = {}
    for m in metas:
        key = m.get("source", "unknown")
        if key not in counts:
            counts[key] = {
                "source": key,
                "category": m.get("category", ""),
                "language": m.get("language", ""),
                "chunks": 0,
            }
        counts[key]["chunks"] += 1
    return {"sources": list(counts.values()), "total_docs": _collection.count()}


@router.delete("/source/{source_name}")
async def delete_source(source_name: str, user: dict = Depends(get_admin_user)):
    """Admin: delete all chunks belonging to a given source."""
    await _ensure_initialized()
    _collection.delete(where={"source": source_name})
    return {"deleted_source": source_name, "remaining_docs": _collection.count()}
