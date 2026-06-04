"""AI Distractor Generator — calls OpenRouter to generate plausible wrong answers."""
import os, re, httpx, json, asyncio
from database import logger

OR_KEY = os.environ.get("OPENROUTER_API_KEY")
OR_URL = "https://openrouter.ai/api/v1/chat/completions"
OR_MODEL = "deepseek/deepseek-chat"
OR_HEADERS = {
    "Authorization": f"Bearer {OR_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://mcq-medical-prep.academy",
    "X-Title": "PrepAcademy",
}
MAX_OPTIONS = 5
MAX_BATCH = 50
MAX_RETRIES = 3


def _next_letter(index: int) -> str:
    return chr(ord("A") + index)


def _option_text(index: int, text: str) -> str:
    return f"{_next_letter(index)}) {text}"


async def generate_distractors(
    question: str,
    correct_answers: list[str],
    existing_options: list[str],
    count: int,
) -> list[str]:
    """Generate `count` plausible distractors for a single question."""
    if count < 1:
        return []
    if not OR_KEY:
        logger.error("[OPTION_GEN] OPENROUTER_API_KEY not set")
        return []

    existing_texts = [
        re.sub(r"^[A-Za-z][.)]\s*", "", opt).strip()
        for opt in existing_options
    ]
    correct_texts = [
        re.sub(r"^[A-Za-z][.)]\s*", "", ca).strip()
        for ca in correct_answers
    ]
    forbidden = set(t.lower() for t in existing_texts + correct_texts)

    next_idx = len(existing_options)
    prompt = (
        f"You are a medical exam question writer. "
        f"Generate exactly {count} plausible but incorrect answer options (distractors) for the following question.\n\n"
        f"Question: {question}\n"
        f"Correct answer(s): {', '.join(correct_texts)}\n"
        f"Existing options: {', '.join(existing_texts)}\n\n"
        f"Requirements:\n"
        f"- Generate exactly {count} new distractors\n"
        f"- Each must be medically plausible but clearly incorrect\n"
        f"- Do NOT duplicate existing options or correct answer(s)\n"
        f"- Return one distractor per line, no numbering or letters\n"
        f"- Do not include any explanation or prefix"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                OR_URL,
                headers=OR_HEADERS,
                json={
                    "model": OR_MODEL,
                    "messages": [
                        {"role": "system", "content": "You generate medical MCQ distractors. Return only the distractor texts, one per line."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 300,
                    "temperature": 0.7,
                },
            )
        d = r.json()
        content = d.get("choices", [{}])[0].get("message", {}).get("content", "")
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    except Exception as e:
        logger.error(f"[OPTION_GEN] API call failed: {e}")
        return []

    lines = [line.strip().rstrip(".") for line in content.split("\n") if line.strip()]
    results = []
    seen = set(o.lower() for o in existing_options)

    for line in lines:
        if len(results) >= count:
            break
        cleaned = re.sub(r"^[A-Za-z][.)]\s*", "", line).strip()
        if not cleaned or len(cleaned) < 3:
            continue
        if cleaned.lower() in forbidden:
            continue
        formatted = _option_text(next_idx + len(results), cleaned)
        if formatted.lower() in seen:
            continue
        seen.add(formatted.lower())
        results.append(formatted)

    if not results:
        logger.warning(f"[OPTION_GEN] No valid distractors generated for: {question[:60]}...")
    return results


async def generate_for_questions(
    questions: list,
    start_index: int = 0,
    max_questions: int = MAX_BATCH,
) -> dict:
    """Batch-generate distractors for a list of ParsedQuestion objects.
    Retries up to MAX_RETRIES times until 5 options reached.
    Questions still below 5 after retries get action='failed_generation'."""
    processed = 0
    updated = 0
    skipped = 0
    failed = 0
    results = []

    batch = questions[start_index: start_index + max_questions]

    for idx, q in enumerate(batch):
        processed += 1
        q_text = q.question if hasattr(q, "question") else (q.get("question") or "")
        existing = q.options if hasattr(q, "options") else (q.get("options") or [])
        correct = q.correct_answers if hasattr(q, "correct_answers") else (q.get("correct_answers") or [])
        generated_so_far = q.generated_options if hasattr(q, "generated_options") else (q.get("generated_options") or [])
        all_options = existing + generated_so_far
        global_idx = start_index + idx

        if len(all_options) >= MAX_OPTIONS:
            skipped += 1
            results.append({"index": global_idx, "question": q_text[:60], "action": "skipped", "reason": f"already has {len(all_options)} options"})
            continue

        new_distractors = []
        retries = 0

        while len(all_options) + len(new_distractors) < MAX_OPTIONS and retries < MAX_RETRIES:
            needed = MAX_OPTIONS - len(all_options) - len(new_distractors)
            current_all = all_options + new_distractors
            chunk = await generate_distractors(q_text, correct, current_all, needed)
            fresh = [d for d in chunk if d not in new_distractors and d not in all_options]
            new_distractors.extend(fresh)
            retries += 1

        final_total = len(all_options) + len(new_distractors)

        if final_total >= MAX_OPTIONS:
            updated += 1
            action = "updated"
        elif new_distractors:
            failed += 1
            action = "failed_generation"
        else:
            failed += 1
            action = "failed"

        results.append({
            "index": global_idx,
            "question": q_text[:60],
            "action": action,
            "generated": new_distractors,
            "retries": retries,
            "final_total": final_total,
        })

    return {"processed": processed, "updated": updated, "skipped": skipped, "failed": failed, "total": len(batch), "results": results}
