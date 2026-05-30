EVAL_QUESTIONS = [
    # ── Kardiologie ──────────────────────────────────────────────────
    {
        "id": "CARD-01",
        "query": "Lungenembolie",
        "expected_keywords": ["Lungenembolie"],
        "category": "Kardiologie",
    },
    {
        "id": "CARD-02",
        "query": "Herzinsuffizienz",
        "expected_keywords": ["Herzinsuffizienz"],
        "category": "Kardiologie",
    },
    {
        "id": "CARD-03",
        "query": "Vorhofflimmern",
        "expected_keywords": ["Vorhofflimmern"],
        "category": "Kardiologie",
    },
    {
        "id": "CARD-04",
        "query": "Was sind die Symptome eines Myokardinfarkts?",
        "expected_keywords": ["Myokardinfarkt"],
        "category": "Kardiologie",
    },
    {
        "id": "CARD-05",
        "query": "Arterielle Hypertonie Behandlung",
        "expected_keywords": ["Hypertonie"],
        "category": "Kardiologie",
    },
    {
        "id": "CARD-06",
        "query": "Aortenklappenstenose",
        "expected_keywords": ["Aortenklappenstenose"],
        "category": "Kardiologie",
    },
    {
        "id": "CARD-07",
        "query": "Perikarditis",
        "expected_keywords": ["Perikarditis"],
        "category": "Kardiologie",
    },
    # ── Pneumologie ──────────────────────────────────────────────────
    {
        "id": "PULM-01",
        "query": "Pneumothorax",
        "expected_keywords": ["Pneumothorax"],
        "category": "Pneumologie",
    },
    {
        "id": "PULM-02",
        "query": "Asthma bronchiale",
        "expected_keywords": ["Asthma"],
        "category": "Pneumologie",
    },
    {
        "id": "PULM-03",
        "query": "COPD",
        "expected_keywords": ["COPD"],
        "category": "Pneumologie",
    },
    {
        "id": "PULM-04",
        "query": "Pneumonie",
        "expected_keywords": ["Pneumonie"],
        "category": "Pneumologie",
    },
    # ── Gastroenterologie ────────────────────────────────────────────
    {
        "id": "GAST-01",
        "query": "Morbus Crohn",
        "expected_keywords": ["Morbus Crohn"],
        "category": "Gastroenterologie",
    },
    {
        "id": "GAST-02",
        "query": "Colitis ulcerosa",
        "expected_keywords": ["Colitis ulcerosa"],
        "category": "Gastroenterologie",
    },
    {
        "id": "GAST-03",
        "query": "Divertikulitis",
        "expected_keywords": ["Divertikulitis"],
        "category": "Gastroenterologie",
    },
    {
        "id": "GAST-04",
        "query": "Akute Pankreatitis Ursachen",
        "expected_keywords": ["Pankreatitis"],
        "category": "Gastroenterologie",
    },
    {
        "id": "GAST-05",
        "query": "Leberzirrhose",
        "expected_keywords": ["Leberzirrhose"],
        "category": "Gastroenterologie",
    },
    {
        "id": "GAST-06",
        "query": "Gastroösophagealer Reflux",
        "expected_keywords": ["Reflux"],
        "category": "Gastroenterologie",
    },
    # ── Neurologie ───────────────────────────────────────────────────
    {
        "id": "NEUR-01",
        "query": "Schlaganfall",
        "expected_keywords": ["Schlaganfall"],
        "category": "Neurologie",
    },
    {
        "id": "NEUR-02",
        "query": "Multiple Sklerose",
        "expected_keywords": ["Multiple Sklerose"],
        "category": "Neurologie",
    },
    {
        "id": "NEUR-03",
        "query": "Morbus Parkinson",
        "expected_keywords": ["Parkinson"],
        "category": "Neurologie",
    },
    {
        "id": "NEUR-04",
        "query": "Epilepsie",
        "expected_keywords": ["Epilepsie"],
        "category": "Neurologie",
    },
    {
        "id": "NEUR-05",
        "query": "Migräne",
        "expected_keywords": ["Migräne"],
        "category": "Neurologie",
    },
    # ── Chirurgie / Orthopädie ───────────────────────────────────────
    {
        "id": "SURG-01",
        "query": "Fraktur",
        "expected_keywords": ["Fraktur"],
        "category": "Chirurgie",
    },
    {
        "id": "SURG-02",
        "query": "Appendizitis",
        "expected_keywords": ["Appendizitis"],
        "category": "Chirurgie",
    },
    {
        "id": "SURG-03",
        "query": "Ileus",
        "expected_keywords": ["Ileus"],
        "category": "Chirurgie",
    },
    {
        "id": "SURG-04",
        "query": "Bandscheibenvorfall",
        "expected_keywords": ["Bandscheibenvorfall"],
        "category": "Chirurgie",
    },
    {
        "id": "SURG-05",
        "query": "Cholezystitis",
        "expected_keywords": ["Cholezystitis"],
        "category": "Chirurgie",
    },
    {
        "id": "SURG-06",
        "query": "Schulterluxation",
        "expected_keywords": ["Schulterluxation"],
        "category": "Chirurgie",
    },
    # ── Nephrologie / Urologie ───────────────────────────────────────
    {
        "id": "NEPH-01",
        "query": "Niereninsuffizienz",
        "expected_keywords": ["Niereninsuffizienz"],
        "category": "Nephrologie",
    },
    {
        "id": "NEPH-02",
        "query": "Harnwegsinfekt",
        "expected_keywords": ["Harnwegsinfekt"],
        "category": "Nephrologie",
    },
    {
        "id": "NEPH-03",
        "query": "Nephrolithiasis Nierensteine",
        "expected_keywords": ["Nierenstein"],
        "category": "Nephrologie",
    },
    {
        "id": "NEPH-04",
        "query": "Benigne Prostatahyperplasie",
        "expected_keywords": ["Prostatahyperplasie"],
        "category": "Nephrologie",
    },
    # ── Endokrinologie ───────────────────────────────────────────────
    {
        "id": "ENDO-01",
        "query": "Diabetes mellitus Typ 2",
        "expected_keywords": ["Diabetes"],
        "category": "Endokrinologie",
    },
    {
        "id": "ENDO-02",
        "query": "Hyperthyreose",
        "expected_keywords": ["Hyperthyreose"],
        "category": "Endokrinologie",
    },
    {
        "id": "ENDO-03",
        "query": "Hashimoto Thyreoiditis",
        "expected_keywords": ["Hashimoto"],
        "category": "Endokrinologie",
    },
    {
        "id": "ENDO-04",
        "query": "Cushing Syndrom",
        "expected_keywords": ["Cushing"],
        "category": "Endokrinologie",
    },
    # ── Infektiologie ────────────────────────────────────────────────
    {
        "id": "INFE-01",
        "query": "Sepsis",
        "expected_keywords": ["Sepsis"],
        "category": "Infektiologie",
    },
    {
        "id": "INFE-02",
        "query": "HIV",
        "expected_keywords": ["HIV"],
        "category": "Infektiologie",
    },
    {
        "id": "INFE-03",
        "query": "Tuberkulose",
        "expected_keywords": ["Tuberkulose"],
        "category": "Infektiologie",
    },
    # ── Hämatologie / Onkologie ──────────────────────────────────────
    {
        "id": "HEMA-01",
        "query": "Anämie",
        "expected_keywords": ["Anämie"],
        "category": "Hämatologie",
    },
    {
        "id": "HEMA-02",
        "query": "Akute Leukämie",
        "expected_keywords": ["Leukämie"],
        "category": "Hämatologie",
    },
    {
        "id": "HEMA-03",
        "query": "Mammakarzinom",
        "expected_keywords": ["Mammakarzinom"],
        "category": "Hämatologie",
    },
    {
        "id": "HEMA-04",
        "query": "Bronchialkarzinom",
        "expected_keywords": ["Bronchialkarzinom"],
        "category": "Hämatologie",
    },
    # ── Notfallmedizin ───────────────────────────────────────────────
    {
        "id": "EMER-01",
        "query": "Anaphylaxie",
        "expected_keywords": ["Anaphylaxie"],
        "category": "Notfallmedizin",
    },
    {
        "id": "EMER-02",
        "query": "Dehydration",
        "expected_keywords": ["Dehydration"],
        "category": "Notfallmedizin",
    },
    {
        "id": "EMER-03",
        "query": "Verbrennung",
        "expected_keywords": ["Verbrennung"],
        "category": "Notfallmedizin",
    },
    {
        "id": "EMER-04",
        "query": "Akute Vergiftung",
        "expected_keywords": ["Vergiftung"],
        "category": "Notfallmedizin",
    },
    # ── Multi-topic queries (test _split_query) ──────────────────────
    {
        "id": "MULT-01",
        "query": "Lungenembolie Pneumothorax Hämatopneumothorax",
        "expected_keywords": ["Pneumothorax"],
        "category": "Split-Test",
    },
    {
        "id": "MULT-02",
        "query": "Morbus Crohn Colitis ulcerosa Divertikulitis",
        "expected_keywords": ["Colitis ulcerosa"],
        "category": "Split-Test",
    },
    {
        "id": "MULT-03",
        "query": "Hypertonie Niereninsuffizienz Diabetes",
        "expected_keywords": ["Niereninsuffizienz"],
        "category": "Split-Test",
    },
]
