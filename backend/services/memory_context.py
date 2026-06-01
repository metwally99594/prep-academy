"""Memory of Mistakes — Tutor prompt prefix builder (Alpha-A).

Returns a compact German sentence injected into the AI tutor's system
prompt so responses can be tailored to the user's known weak areas.

Per Alpha-A decision B, the prompt context includes only the top 3
weaknesses and the weakest specialty. Wrong counts, streak counts, and
7-day totals are intentionally NOT included in the prompt to keep the
LLM focused on the concepts without biasing on noisy counters.
The user-facing badge consumes /api/tutor/context/memory directly and
may display those metrics for transparency.
"""
from tracker import get_weakness_summary


async def build_tutor_memory_prefix(db, user_id: str) -> str:
    """Return a compact prompt-prefix sentence or empty string.

    Defensive: returns "" on missing profile, errors, or empty weaknesses.
    Never raises.
    """
    try:
        summary = await get_weakness_summary(db, user_id, limit=3)
    except Exception:
        return ""

    top = (summary.get("top_weaknesses") or [])[:3]
    if not top:
        return ""

    parts = []
    for w in top:
        concept = (w.get("concept") or "").strip()
        if not concept:
            continue
        specialty = (w.get("specialty_id") or "").strip()
        if specialty:
            parts.append(f"{concept} ({specialty})")
        else:
            parts.append(concept)

    if not parts:
        return ""

    # Weakest specialty — only surface when statistically meaningful (>=10 answered)
    weakest = None
    for s in (summary.get("by_specialty") or []):
        if (s.get("total") or 0) >= 10:
            weakest = s.get("specialty_id")
            break

    sentence = "Hintergrund zum Nutzer: aktuelle Schwächen — " + ", ".join(parts) + "."
    if weakest:
        sentence += f" Schwächstes Fachgebiet: {weakest}."
    sentence += " Berücksichtige diese Schwerpunkte, wenn relevant für die Frage."
    return sentence
