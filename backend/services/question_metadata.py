import re
from typing import Any, Dict, Optional


COUNTRY_ALIASES = {
    "at": "austria",
    "austria": "austria",
    "österreich": "austria",
    "oesterreich": "austria",
    "de": "germany",
    "germany": "germany",
    "deutschland": "germany",
    "ch": "switzerland",
    "switzerland": "switzerland",
    "schweiz": "switzerland",
}

SUBJECT_ALIASES = {
    "innere medizin": "internal",
    "internal medicine": "internal",
    "internal_medicine": "internal",
    "internal": "internal",
    "chirurgie": "surgery",
    "surgery": "surgery",
    "pädiatrie": "pediatrics",
    "paediatrie": "pediatrics",
    "pediatrics": "pediatrics",
    "notfallmedizin": "emergency",
    "emergency": "emergency",
    "ophthalmologie": "ophthalmology",
    "ophthalmology": "ophthalmology",
    "dermatologie": "dermatology",
    "dermatology": "dermatology",
    "hno": "ent",
    "ent": "ent",
    "gynäkologie": "obgyn",
    "gynaekologie": "obgyn",
    "obgyn": "obgyn",
    "neurologie": "neurology",
    "neurology": "neurology",
    "psychiatrie": "psychiatry",
    "psychiatry": "psychiatry",
    "pharmakologie": "pharma",
    "pharma": "pharma",
}

SUBSPECIALTY_ALIASES = {
    "cardiology": "cardiology",
    "kardiologie": "cardiology",
    "kardio": "cardiology",
    "gastroenterology": "gastroenterology",
    "gastroenterologie": "gastroenterology",
    "pneumology": "pneumology",
    "pneumologie": "pneumology",
    "nephrology": "nephrology",
    "nephrologie": "nephrology",
    "endocrinology": "endocrinology",
    "endokrinologie": "endocrinology",
    "hematology": "hematology",
    "hämatologie": "hematology",
    "haematologie": "hematology",
}

CITY_ALIASES = {
    "wien": "vienna",
    "vienna": "vienna",
    "sip4": "sip4",
    "sip_4": "sip4",
    "sip 4": "sip4",
    "sip4a": "sip4",
    "sip5": "sip5",
    "sip_5": "sip5",
    "sip 5": "sip5",
    "sip5a": "sip5",
    "innsbruck": "innsbruck",
    "graz": "graz",
    "linz": "linz",
    "salzburg": "salzburg",
    "hamburg": "hamburg",
    "berlin": "berlin",
    "muenchen": "munich",
    "munich": "munich",
    "münchen": "munich",
    "frankfurt": "frankfurt",
    "frankfurt_am_main": "frankfurt",
    "koeln": "cologne",
    "köln": "cologne",
    "cologne": "cologne",
    "duesseldorf": "duesseldorf",
    "düsseldorf": "duesseldorf",
    "dusseldorf": "duesseldorf",
    "bern": "bern",
    "berne": "bern",
    "zuerich": "zurich",
    "zürich": "zurich",
    "zurich": "zurich",
    "basel": "basel",
    "genf": "geneva",
    "geneva": "geneva",
    "lausanne": "lausanne",
    "andere": "andere",
    "other": "andere",
}

EXAM_SYSTEM_ALIASES = {
    "eidgenoessische_pruefung": "eidgenoessische_pruefung",
    "eidgenossische_prufung": "eidgenoessische_pruefung",
    "eidgenössische prüfung": "eidgenoessische_pruefung",
    "eidgenoessische pruefung": "eidgenoessische_pruefung",
    "federal_medical_exam": "eidgenoessische_pruefung",
    "federal licensing examination": "eidgenoessische_pruefung",
    "mebeko": "mebeko",
}

EXAM_PART_ALIASES = {
    "mc": "mc",
    "mc_pruefung": "mc",
    "mc-pruefung": "mc",
    "mc-prufung": "mc",
    "mc prüfung": "mc",
    "mc pruefung": "mc",
    "multiple_choice": "mc",
    "clinical_skills": "clinical_skills",
    "clinical skills": "clinical_skills",
    "osce": "clinical_skills",
    "praktisch": "clinical_skills",
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _slug(value: Any) -> str:
    text = _clean(value).lower()
    text = (
        text.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _first_non_empty(*values: Any) -> Optional[str]:
    for value in values:
        cleaned = _clean(value)
        if cleaned:
            return cleaned
    return None


def _normalize_subject_id(value: Any) -> Optional[str]:
    cleaned = _clean(value)
    if not cleaned:
        return None
    return SUBJECT_ALIASES.get(cleaned.lower(), _slug(cleaned))


def _normalize_subspecialty_id(value: Any) -> Optional[str]:
    cleaned = _clean(value)
    if not cleaned:
        return None
    return SUBSPECIALTY_ALIASES.get(cleaned.lower(), _slug(cleaned))


def _extract_nested_id_name(value: Any) -> tuple[Optional[str], Optional[str]]:
    if isinstance(value, dict):
        raw_id = _first_non_empty(value.get("id"), value.get("key"), value.get("slug"))
        raw_name = _first_non_empty(value.get("name_de"), value.get("name"), value.get("label_de"), value.get("label"), raw_id)
        return raw_id, raw_name
    raw = _first_non_empty(value)
    return raw, raw


def normalize_question_metadata(question: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize old flat imports and the new country/city/subject/subspecialty schema."""
    q = dict(question or {})

    subject = q.get("subject")
    subject_id = _first_non_empty(q.get("subject_id"))
    subject_name = _first_non_empty(q.get("subject_name_de"), q.get("subject_name"))

    if isinstance(subject, dict):
        raw_subject_id, raw_subject_name = _extract_nested_id_name(subject)
        subject_id = subject_id or raw_subject_id
        subject_name = subject_name or raw_subject_name
        branch = (
            subject.get("specialty")
            or subject.get("subspecialty")
            or subject.get("branch")
            or subject.get("topic")
        )
    else:
        raw_subject_id, raw_subject_name = _extract_nested_id_name(subject)
        subject_id = subject_id or raw_subject_id
        subject_name = subject_name or raw_subject_name
        branch = q.get("subspecialty") or q.get("branch") or q.get("topic")

    branch_id, branch_name = _extract_nested_id_name(branch)
    subspecialty_id = _first_non_empty(q.get("subspecialty_id"), q.get("branch_id"), q.get("topic_id"), branch_id)
    subspecialty_name = _first_non_empty(
        q.get("subspecialty_name_de"),
        q.get("subspecialty_name"),
        q.get("branch_name_de"),
        q.get("branch_name"),
        branch_name,
    )

    specialty_source = q.get("specialty")
    flat_specialty = specialty_source if isinstance(specialty_source, str) else None
    specialty_id = _first_non_empty(q.get("specialty_id"), q.get("fach"), flat_specialty, subject_id)
    subject_id = _normalize_subject_id(subject_id or specialty_id)
    specialty_id = _normalize_subject_id(specialty_id or subject_id) or ""
    subspecialty_id = _normalize_subspecialty_id(subspecialty_id)

    city = _first_non_empty(
        q.get("city"),
        q.get("exam_location"),
        q.get("stadt"),
        q.get("ort"),
        q.get("location"),
    )
    city_slug = CITY_ALIASES.get(city.lower(), _slug(city)) if city else None
    country = _first_non_empty(q.get("country"), q.get("land"))
    country_slug = COUNTRY_ALIASES.get(country.lower(), _slug(country)) if country else None
    exam_system = _first_non_empty(q.get("exam_system"), q.get("exam"), q.get("prüfungssystem"), q.get("pruefungssystem"))
    exam_system_slug = EXAM_SYSTEM_ALIASES.get(exam_system.lower(), _slug(exam_system)) if exam_system else None
    exam_part = _first_non_empty(q.get("exam_part"), q.get("exam_section"), q.get("prüfungsteil"), q.get("pruefungsteil"))
    exam_part_slug = EXAM_PART_ALIASES.get(exam_part.lower(), _slug(exam_part)) if exam_part else None

    tags = list(q.get("tags") or [])
    for tag in (subject_id, subject_name, subspecialty_id, subspecialty_name, country_slug, city_slug, exam_system_slug, exam_part_slug):
        if tag and tag not in tags:
            tags.append(tag)

    normalized = {
        "specialty_id": specialty_id,
        "subject_id": subject_id or specialty_id,
        "subject_name_de": subject_name,
        "subspecialty_id": subspecialty_id,
        "subspecialty_name_de": subspecialty_name,
        "city": city_slug,
        "exam_location": city_slug,
        "country": country_slug,
        "exam_system": exam_system_slug,
        "exam_part": exam_part_slug,
        "tags": tags,
    }
    return {k: v for k, v in normalized.items() if v not in (None, "")}
