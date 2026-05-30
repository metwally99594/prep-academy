import json, os, asyncio, logging, re, httpx
logger = logging.getLogger(__name__)

# ── Model configuration ─────────────────────────────────────────────
TIER1_MODELS = [
    ("DeepSeek",  "deepseek/deepseek-chat"),
    ("Qwen",      "qwen/qwen-2.5-32b"),
    ("InternLM",  "internlm/internlm3-8b"),
]

TIER2_MODELS = TIER1_MODELS + [
    ("GPT-4o",    "openai/gpt-4o"),
    ("Claude",    "anthropic/claude-sonnet-4"),
    ("Gemini",    "google/gemini-2.0-flash-001"),
]

SYSTEM_PROMPT = """Du bist ein medizinischer Experte im Metsu-Konsensuspaneel.

Antworte NUR im folgenden JSON-Format, kein anderer Text:
{
  "answer": "Deine Antwort basierend auf den Dokumenten",
  "confidence": 0.91,
  "citations": ["Seite X", "Seite Y"],
  "reasoning_summary": "Kurze Zusammenfassung"
}

REGELN:
1. Nutze NUR die bereitgestellten INFORMATIONEN
2. Zitiere mit Seitenzahlen aus [DOKUMENT N]
3. Sei präzise, akademisch
4. confidence 0.0–1.0: wie sicher die Antwort in den Quellen ist
5. Antwort nur auf Deutsch
6. Valides JSON, kein sonstiger Text"""


async def _call_or(model_name: str, system: str, user: str, timeout: float = 30.0) -> dict | None:
    or_key = os.environ.get("OPENROUTER_API_KEY")
    if not or_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=timeout) as cl:
            r = await cl.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {or_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://prepacademy-med.com",
                    "X-Title": "PrepAcademy Metsu",
                },
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": 600,
                    "temperature": 0.3,
                },
            )
            d = r.json()
            if "choices" not in d or not d["choices"]:
                return None
            raw = d["choices"][0]["message"]["content"] or ""
            raw = re.sub(r"```json\s*", "", raw)
            raw = re.sub(r"\s*```", "", raw)
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            # Try JSON parse, fallback to string answer
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict) and "answer" in parsed:
                    return parsed
            except json.JSONDecodeError:
                pass
            # Fallback: wrap raw text as answer
            return {"answer": raw, "confidence": 0.5, "citations": [], "reasoning_summary": ""}
    except Exception as e:
        logger.debug(f"Metsu call failed for {model_name}: {e}")
        return None


def _jaccard_similarity(a: str, b: str) -> float:
    tok_a = set(re.findall(r'\w+', a.lower()))
    tok_b = set(re.findall(r'\w+', b.lower()))
    if not tok_a or not tok_b:
        return 0.0
    return len(tok_a & tok_b) / len(tok_a | tok_b)


def _compute_agreement(responses: list[dict]) -> dict:
    if len(responses) < 2:
        return {"agreement_score": 1.0, "agree_count": len(responses), "total": len(responses), "pairs": []}

    pairwise = []
    for i in range(len(responses)):
        for j in range(i + 1, len(responses)):
            sim = _jaccard_similarity(
                responses[i].get("answer", ""), responses[j].get("answer", "")
            )
            pairwise.append((i, j, sim))

    avg_sim = sum(p[2] for p in pairwise) / len(pairwise) if pairwise else 1.0
    threshold = 0.35

    # Count how many models agree with the majority
    agree_counts = [0] * len(responses)
    for i, j, sim in pairwise:
        if sim >= threshold:
            agree_counts[i] += 1
            agree_counts[j] += 1

    max_agree = max(agree_counts) if agree_counts else 0
    majority = max_agree >= (len(responses) - 1)  # agrees with at least N-1 others

    return {
        "agreement_score": round(avg_sim, 3),
        "agree_count": max_agree + 1,
        "total": len(responses),
        "majority": majority,
        "pairwise_similarities": [round(p[2], 3) for p in pairwise],
    }


def _merge_citations(responses: list[dict]) -> list[str]:
    seen = set()
    merged = []
    for r in responses:
        for c in r.get("citations", []):
            c = str(c).strip()
            if c and c not in seen:
                seen.add(c)
                merged.append(c)
    return merged


async def run_consensus(
    question: str,
    evidence: str,
    force_full: bool = False,
) -> dict:
    """Run Metsu consensus. Tier 1 (3 models) by default, Tier 2 (6 models) if forced or disagreement."""
    user_msg = f"FRAGE:\n{question}\n\nINFORMATIONEN:\n{evidence}"

    # ── Tier 1 ──────────────────────────────────────────────────────
    tier1_tasks = [_call_or(m, SYSTEM_PROMPT, user_msg) for _, m in TIER1_MODELS]
    tier1_results = await asyncio.gather(*tier1_tasks)
    tier1_valid = [r for r in tier1_results if r is not None]

    responses = tier1_valid
    used_tier2 = False

    if not force_full and tier1_valid:
        agreement = _compute_agreement(tier1_valid)
        avg_conf = sum(r.get("confidence", 0.5) for r in tier1_valid) / len(tier1_valid)
        logger.info(f"Metsu T1: agreement={agreement['agreement_score']} majority={agreement['majority']} avg_conf={avg_conf:.2f}")

        if agreement["majority"] and avg_conf >= 0.6 and agreement["agreement_score"] >= 0.35:
            # Tier 1 consensus reached
            best = max(tier1_valid, key=lambda r: r.get("confidence", 0))
            return {
                "answer": best["answer"],
                "confidence": round(avg_conf, 2),
                "agreement": agreement["agreement_score"],
                "models_used": len(tier1_valid),
                "models_total": len(TIER1_MODELS),
                "citations": _merge_citations(tier1_valid),
                "reasoning": best.get("reasoning_summary", ""),
                "tier": 1,
                "model_details": [
                    {"name": TIER1_MODELS[i][0], "confidence": r.get("confidence", 0)}
                    for i, r in enumerate(tier1_valid)
                ],
            }

    # ── Tier 2 (escalation) ─────────────────────────────────────────
    used_tier2 = True
    disagreement_context = ""
    if tier1_valid:
        disagreement_context = "\n\nVORHERIGE ANTWORTEN:\n"
        for i, r in enumerate(tier1_valid):
            disagreement_context += (
                f"=== {TIER1_MODELS[i][0]} (confidence: {r.get('confidence', 0):.2f}) ===\n"
                f"Antwort: {r.get('answer', '')}\n"
                f"Begründung: {r.get('reasoning_summary', '')}\n\n"
            )

    tier2_user_msg = (
        f"FRAGE:\n{question}\n\nINFORMATIONEN:\n{evidence}"
        + disagreement_context
        + "\n\nBitte antworte erneut im JSON-Format. Berücksichtige die vorherigen Antworten."
    )

    tier2_tasks = [_call_or(m, SYSTEM_PROMPT, tier2_user_msg) for _, m in TIER2_MODELS]
    tier2_results = await asyncio.gather(*tier2_tasks)
    tier2_valid = [r for r in tier2_results if r is not None]

    if not tier2_valid:
        # Fallback: best of tier1
        if tier1_valid:
            best = max(tier1_valid, key=lambda r: r.get("confidence", 0))
            return {
                "answer": best["answer"],
                "confidence": 0.5,
                "agreement": 0.0,
                "models_used": 1,
                "models_total": len(TIER2_MODELS),
                "citations": best.get("citations", []),
                "reasoning": best.get("reasoning_summary", ""),
                "tier": 1,
                "model_details": [],
            }
        return {"error": "All models failed", "tier": 1, "answer": "Entschuldigung, alle Modelle sind fehlgeschlagen.", "confidence": 0.0, "agreement": 0.0, "models_used": 0, "models_total": len(TIER2_MODELS), "citations": [], "reasoning": "", "model_details": []}

    responses = tier2_valid
    agreement = _compute_agreement(tier2_valid)
    avg_conf = sum(r.get("confidence", 0.5) for r in tier2_valid) / len(tier2_valid)

    # Pick best answer (highest confidence among majority)
    best = max(tier2_valid, key=lambda r: r.get("confidence", 0))
    all_models = TIER2_MODELS if used_tier2 else TIER1_MODELS

    return {
        "answer": best["answer"],
        "confidence": round(avg_conf, 2),
        "agreement": agreement["agreement_score"],
        "models_used": len(tier2_valid),
        "models_total": len(TIER2_MODELS),
        "citations": _merge_citations(tier2_valid),
        "reasoning": best.get("reasoning_summary", ""),
        "tier": 2,
        "model_details": [
            {"name": all_models[i][0], "confidence": r.get("confidence", 0)}
            for i, r in enumerate(tier2_valid)
        ],
    }


async def search_and_consensus(question: str, specialty_id: str = None, chapter_index: int = None, force_full: bool = False) -> dict:
    """Qdrant → evidence → Metsu consensus. Falls back to simple answer if Qdrant unavailable."""
    from vector_store import search_chapters

    evidence = ""
    evidence_objects = []
    try:
        results = search_chapters(question, specialty_id=specialty_id, chapter_index=chapter_index, limit=5)
        if results:
            parts = []
            for i, d in enumerate(results, 1):
                parts.append(f"[DOKUMENT {i}] {d['filename']} — {d.get('chapter_title', '')} (Seite {d.get('page_start', '?')}–{d.get('page_end', '?')}):\n{d.get('text', '')}")
                excerpt = (d.get("text") or "")[:500]
                if len(d.get("text") or "") > 500:
                    excerpt += "..."
                evidence_objects.append({
                    "filename": d.get("filename", ""),
                    "chapter": d.get("chapter_title", ""),
                    "page_start": d.get("page_start"),
                    "page_end": d.get("page_end"),
                    "excerpt": excerpt,
                })
            evidence = "\n\n".join(parts)
    except Exception as e:
        logger.warning(f"Metsu Qdrant search failed: {e}")

    if not evidence:
        return {
            "answer": "Keine relevanten Dokumente gefunden.",
            "confidence": 0.0,
            "agreement": 1.0,
            "models_used": 0,
            "models_total": 0,
            "citations": [],
            "reasoning": "Keine Dokumente in der Wissensdatenbank gefunden.",
            "tier": 0,
            "model_details": [],
            "evidence": [],
            "error": "no_documents",
        }

    result = await run_consensus(question, evidence, force_full=force_full)
    result["evidence"] = evidence_objects
    return result
