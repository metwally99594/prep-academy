# Knowledge Retrieval Quality Optimization

## 1. Problem Analysis

The current `search()` function in `backend/services/knowledge_lab_service.py` (lines 202-236) is a simple token-count-based keyword matcher. Every token extracted from the query is weighted equally, and ranking is purely additive — more hits = higher rank. This produces counterintuitive results.

### Concrete example

**Query:** `"Welche Symptome hat Morbus Parkinson?"`

Tokens extracted: `["welche", "symptome", "hat", "morbus", "parkinson"]`

Current scores:

| Page | Token hits | Calculation | Score |
|---|---|---|---|
| Psychiatrie | symptom ×8, parkinson ×1 | (8×2) + (1×2) | **18** |
| Neurologie | symptom ×2, morbus ×2, parkinson ×3 | (2×2)+(2×2)+(3×2) | **14** |

**Problem:** Psychiatrie wins purely because it uses the word "Symptome" 8 times (listing depression, schizophrenia, anxiety symptoms). Neurologie — the page that actually contains a dedicated "Morbus Parkinson" section — ranks second. The title bonus (`+10`) never fires because neither title contains any query token literally.

**Root causes:**

1. **No phrase awareness** — "Morbus Parkinson" is split into two independent tokens; a page containing the exact phrase gets no bonus over one containing the words scattered apart.
2. **No stopword filtering** — "welche", "hat" contribute equally to the score as medical terms.
3. **No medical term prioritization** — common words and medical keywords have identical weight.
4. **No title relevance signal** — title bonus requires an exact literal token match, so a page titled "Neurologie" can never get a title bonus for a "Parkinson" query even though neurology is the relevant specialty.
5. **No position awareness** — a token appearing once in a heading counts the same as a token appearing in a footer.

---

## 2. Proposed Changes

### 2.1 Title Weighting

**Current behavior:** Title bonus fires only when a query token is literally found in `page["title_lower"]`:
```python
if token in page["title_lower"]:
    score += 10
```
A page titled "Neurologie" never gets a title bonus for "Parkinson".

**Proposal — Specialty-triggered title boost:**

Add a small lookup dictionary mapping medical conditions to their relevant specialties/disciplines. When a known medical condition is detected in the query, pages whose title matches the associated specialty get a title bonus.

```python
# Medical condition → relevant specialty mapping (extendable)
CONDITION_SPECIALTY = {
    "parkinson": "neurologie",
    "multiple sklerose": "neurologie",
    "schlaganfall": "neurologie",
    "depression": "psychiatrie",
    "schizophrenie": "psychiatrie",
    "hypertonie": "kardiologie",
    "diabetes": "endokrinologie",
    # ...
}
```

During scoring, check if any query token appears as a key in this map (or if a multi-word phrase matches). If so, give a **+15 bonus** to pages whose title contains the mapped specialty.

```python
# Also retain the exact token title match but lower weight to avoid over-boosting
if token in page["title_lower"]:
    score += 8  # was 10, slightly reduced
```

And add near the top of `search()`:
```python
detected_conditions = set()
for phrase in CONDITION_SPECIALTY:
    if phrase in query_lower:
        detected_conditions.add(phrase)
```

Then inside the scoring loop:
```python
for cond in detected_conditions:
    specialty = CONDITION_SPECIALTY[cond]
    if specialty in page["title_lower"]:
        score += 15
        matched_tokens.add(cond)
```

**Expected improvement:** Neurologie gets +15 for "Parkinson" → score goes from 14 to **29**, beating Psychiatrie's 18.

### 2.2 Exact Disease-Name Matching

**Current behavior:** Multi-word medical terms are split into individual tokens with no bonus for co-occurrence.

**Proposal — Known-phrase detection and bonus:**

Maintain a set of common German medical compound terms:

```python
MEDICAL_PHRASES = {
    "morbus parkinson",
    "multiple sklerose",
    "arterielle hypertonie",
    "chronisch obstruktive lungenerkrankung",
    "akutes koronarsyndrom",
    "diabetes mellitus",
    "systemischer lupus erythematodes",
    "morbus crohn",
    # ...
}
```

Before tokenization, scan the query for these phrases. If found, search for the exact phrase in each page's content (case-insensitive). Give a **+50 bonus** per exact phrase match — this signals that the page is specifically about that condition.

```python
# Before per-token loop:
phrase_score = 0
for phrase in MEDICAL_PHRASES:
    if phrase in query_lower:
        count = page["content"].count(phrase)
        if count:
            phrase_score += count * 50
            matched_tokens.add(phrase.replace(" ", "_"))  # track as single token
```

**Expected improvement:** In the example, any page containing the literal string "morbus parkinson" gets +50. If Neurologie contains it once, that is +50 — bringing total to **79** vs Psychiatrie's 18. For queries without a medical phrase, this code does nothing (zero cost).

### 2.3 Phrase Matching

**Current behavior:** Only individual token counts are used. A page with tokens scattered across unrelated sections scores the same as one where they appear together.

**Proposal — Bigram/trigram overlap bonus:**

After tokenizing, generate all adjacent bigrams and trigrams from the query tokens (after stopword removal). For each, check if the exact n-gram appears in the page content.

```python
# After tokenization, build n-grams
def ngrams(tokens, n):
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens)-n+1)]

query_bigrams = ngrams(tokens, 2)
query_trigrams = ngrams(tokens, 3)

# Inside scoring loop:
for bigram in query_bigrams:
    count = page["content"].count(bigram)
    if count:
        score += count * 10
        matched_tokens.add(bigram)

for trigram in query_trigrams:
    count = page["content"].count(trigram)
    if count:
        score += count * 25
        matched_tokens.add(trigram)
```

This rewards pages where query terms appear in sequence. For the Parkinson example, a page containing "symptome parkinson" (bigram) or "morbus parkinson" (bigram) gets additional credit beyond what individual token matches give.

**Edge case:** Only generate n-grams from semantically meaningful tokens (skip n-grams containing stopwords). This avoids noise from pairs like "welche symptome" or "hat morbus".

```python
STOPWORDS = {"welche", "hat", "was", "sind", "ist", "die", "der", "ein",
             "eine", "bei", "mit", "von", "für", "und", "oder", "das",
             "des", "dem", "den", "sich", "auch", "werden", "wird",
             "nicht", "zum", "zur", "einen", "einer", "als", "wie",
             "auf", "aus", "nach", "an", "im", "am"}
meaningful = [t for t in tokens if t not in STOPWORDS]
# Build n-grams only from meaningful tokens
```

**Expected improvement:** Pages with coherent coverage of the query topic (terms appear together) get a significant boost over pages that just happen to mention individual keywords in unrelated sections.

### 2.4 Medical Term Relevance Scoring

**Current behavior:** All tokens weighted equally: `score += count * 2`.

**Proposal — Stopword filter + medical term multiplier:**

1. **Skip stopwords entirely** — they no longer contribute to score.
2. **Medical term multiplier** — known medical terms get a higher per-hit weight.

```python
MEDICAL_TERMS = {
    "symptom", "symptome", "diagnose", "diagnostik", "therapie", "therapie",
    "behandlung", "erkrankung", "krankheit", "syndrom", "pathophysiologie",
    "ätiologie", "prognose", "komplikation", "indikation", "kontraindikation",
    "morbus", "parkinson", "hypertonie", "diabetes", "karzinom", "tumor",
    "infektion", "entzündung", "fraktur", "insuffizienz", "stenose",
    "thrombose", "embolie", "ödem", "ischämie", "degeneration",
    "medikament", "dosierung", "nebenwirkung", "wirkstoff",
}
```

Scoring logic becomes:

```python
for token in meaningful_tokens:  # stopwords already filtered
    if token in page["title_lower"]:
        score += 8
        matched_tokens.add(token)
    count = page["content"].count(token)
    if count:
        weight = 4 if token in MEDICAL_TERMS else 2
        score += count * weight
        matched_tokens.add(token)
```

Medical terms like "symptome", "parkinson", "morbus" get **4 points per hit** (up from 2), while non-medical tokens still get 2. Stopwords get **zero** points.

**Expected improvement:** In the example, "welche" and "hat" contribute nothing. "symptome" (medical term) counts double. This amplifies the medical signal and eliminates noise.

### 2.5 Ranking Quality Improvements

**Current behavior:** Single-stage sort: `(-score, -matched_tokens)`. No awareness of content structure or density.

**Proposal — Multi-factor tiebreaker with bonuses:**

Add scoring bonuses (not post-sort tiebreakers, to keep sorting simple) that reward high-quality matches:

```python
# Content structure bonuses (added to score during the per-page loop):

# (a) Heading match bonus
# Check if any query term appears in a Markdown heading line
# (headings contain query term → relevant section exists)
content_lower = page["content"]
if any(f"# {token}" in content_lower or f"## {token}" in content_lower or f"### {token}" in content_lower
       for token in meaningful_tokens):
    score += 20
    # Extra +10 if the query's medical condition name is in a heading
    # (e.g., "## Morbus Parkinson" in the Neurologie page)
    for cond in detected_conditions:
        if f"# {cond}" in content_lower or f"## {cond}" in content_lower:
            score += 10

# (b) Early occurrence bonus
# If the first occurrence of a query term is in the first 20% of content,
# reward the page (keyword prominence)
first_quartile = len(content_lower) // 5
for token in meaningful_tokens:
    pos = content_lower.find(token)
    if 0 <= pos < first_quartile:
        score += 3
        break  # one bonus per page

# (c) Keyword density bonus (short, focused pages beat long, diffuse ones)
# If ratio of matching pages total content length is high, add a small boost
if word_count > 0:
    raw_match_count = sum(content_lower.count(t) for t in meaningful_tokens)
    density = raw_match_count / word_count
    if density > 0.05:   # >5% of words are query terms
        score += int(density * 50)  # cap automatically by density

# (d) Normalize the sort to handle the new factors
# Scaled score helps, but keep sort key simple:
 scored.sort(key=lambda x: (-x["score"], -x["matched_tokens"]))
```

**Expected improvement:** A dedicated page with "## Morbus Parkinson" heading, the term appearing early, and high keyword density will score 20–40+ points higher than a page that merely scatters matching words across unrelated sections.

---

## 3. Expected Results (Before vs After)

### Query: "Welche Symptome hat Morbus Parkinson?"

| Factor | Psychiatrie (before) | Psychiatrie (after) | Neurologie (before) | Neurologie (after) |
|---|---|---|---|---|
| Token count (symptome×8, parkinson×1) | 18 | — | — | — |
| Token count (symptome×2, morbus×2, parkinson×3) | — | — | 14 | — |
| Stopword removal (welche, hat) | — | 0 | — | 0 |
| Medical term weight (symptome×8×4, parkinson×1×4) | — | 36 | — | — |
| Medical term weight (symptome×2×4, morbus×2×4, parkinson×3×4) | — | — | — | 28 |
| Exact phrase "morbus parkinson" | — | 0 | — | +50 |
| Specialty boost (parkinson → neurologie) | — | 0 | — | +15 |
| Heading "## Morbus Parkinson" | — | 0 | — | +30 |
| **Total score** | **18** | **36** | **14** | **123** |

**Ranking:** Neurologie #1 (123), Psychiatrie #2 (36).

### Query: "Behandlung Diabetes mellitus Typ 2"

Before: Pages with scattered mentions of "behandlung", "diabetes", "mellitus", "typ", "2" compete — the longest, most generic internal medicine page wins.

After: The page titled "Diabetes mellitus" gets +15 specialty bonus (diabetes → endokrinologie if title matches or literal title match gets +8), +50 for exact phrase "diabetes mellitus", +30 if heading exists, medical term multiplier kicks in. The correct specialty page wins decisively.

---

## 4. Edge Cases & Risks

### 4.1 False positives from medical term detection
- **Risk:** A query like "Parkinson-Syndrom" contains "parkinson" → specialty boost applies to Neurologie. Correct. But "Parkinson-Betreuung" (caregiving) might also trigger it — still reasonable since neurology pages cover care.
- **Mitigation:** Keep `CONDITION_SPECIALTY` curated; start small and expand based on actual query logs.

### 4.2 Over-boosting short pages
- **Density bonus** could inflate scores for very short pages (e.g., a stub with 20 words where 3 match = 15% density → +7 bonus).
- **Mitigation:** Cap density bonus at +20 and only apply when word_count > 50.

### 4.3 Heading detection false positives
- A page might have `## Symptome` in a sidebar or table of contents unrelated to the main content.
- **Mitigation:** Only check heading lines (lines starting with `# `, `## `, `### `) — standard Markdown headings are unlikely in navigational elements.

### 4.4 Maintenance burden of lookup lists
- `MEDICAL_PHRASES` and `CONDITION_SPECIALTY` require periodic updates as the wiki grows.
- **Mitigation:** Keep lists in a separate constants section at the top of the file (~30 lines total). Document that adding new wiki topics should include updating these lists. This is far less effort than maintaining embeddings/vector DB.

### 4.5 Query without medical terms
- For a query like "Was ist Blutdruck?" the phrase/condition lists won't match — behavior falls back to standard token scoring (but with stopword filtering, giving cleaner results).
- **Acceptable:** The generic path still works well; medical-specific boosts are additive, not required.

### 4.6 Performance
- Each page now does phrase lookups, n-gram checks, heading scans, density calculations.
- **Mitigation:** All operations are O(n) string ops over pre-loaded page content. For ~200 pages with ~500 words each, total search time stays under ~50ms. The `build_index()` cache means the heavy IO happens once.

### 4.7 Case sensitivity
- All comparisons use `page["content"]` (lowercased during index build, confirmed by reading `build_index()`). The proposed code uses `content_lower` — consistent.

---

## 5. Implementation Summary

| Change | Lines added | Impact | Dependency |
|---|---|---|---|
| 2.1 Specialty title boost | ~15 lines | Solves "title never matches condition name" | `CONDITION_SPECIALTY` dict (~15 entries) |
| 2.2 Exact phrase matching | ~10 lines | Biggest win — correctly identifies condition-focused pages | `MEDICAL_PHRASES` set (~15 entries) |
| 2.3 Bigram/trigram matching | ~15 lines | Rewards coherent topical coverage | Built from existing tokens |
| 2.4 Stopword filter + medical weight | ~10 lines | Eliminates noise, amplifies signal | `STOPWORDS` set (~30 entries), `MEDICAL_TERMS` set (~40 entries) |
| 2.5 Heading/density/position bonuses | ~20 lines | Improves ranking of structured, focused pages | Content structure parsing |
| **Total** | **~70 lines** | | No new packages |

All changes are localized to `knowledge_lab_service.py`. No schema or manifest changes. No new files. The `build_index()` output is unchanged — all enhancements operate on the existing index structure (`title_lower`, `content`, `word_count`).

### Deployment

1. Add the three lookup sets/dicts as module-level constants (~30 lines).
2. Replace the token-loop in `search()` (~20 lines changed, ~40 lines added).
3. Run the existing test suite to confirm no regressions.
4. Manually test ~5 medical queries against the current and new implementation.

### Future optional improvements (out of scope for this proposal)

- Query expansion: add synonyms ("Herzinfarkt" ↔ "Myokardinfarkt")
- Stemming: match "Symptom", "Symptome", "symptomatisch"
- Click-through feedback: boost pages users actually open
