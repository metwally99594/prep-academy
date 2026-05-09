"""
Findings Vocabulary — Data Consistency Tests.

Verifies that findings_vocabulary.py is internally consistent and that
dependent modules (analyzer_prompts) correctly import from it.

No LLM calls. No server needed.
Run with: pytest backend/tests/test_findings_vocabulary.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.findings_vocabulary import (
    ANATOMY_TERMS,
    MODALITY_CONSTRAINTS,
    MODALITY_TERM_BLACKLIST,
    MEDICAL_VOTE_TERMS,
    FINDING_SEVERITY,
    LANGUAGE_GATE,
    FORBIDDEN_PHRASES_ALWAYS,
    CATEGORY_KEYWORDS,
)


# ═══════════════════════════════════════════════════════════════
# ANATOMY TERMS
# ═══════════════════════════════════════════════════════════════

class TestAnatomyTerms:
    def test_is_list(self):
        assert isinstance(ANATOMY_TERMS, list)

    def test_non_empty(self):
        assert len(ANATOMY_TERMS) > 0

    def test_no_duplicates(self):
        assert len(ANATOMY_TERMS) == len(set(ANATOMY_TERMS))

    def test_all_strings(self):
        for t in ANATOMY_TERMS:
            assert isinstance(t, str) and t, f"Non-string or empty term: {t!r}"

    def test_core_regions_present(self):
        required = {"thorax", "lungs", "heart", "abdomen", "spine", "bones"}
        missing = required - set(ANATOMY_TERMS)
        assert not missing, f"Missing core anatomy terms: {missing}"

    def test_no_whitespace_in_simple_terms(self):
        """Terms should use underscores not spaces (e.g. soft_tissue)."""
        for t in ANATOMY_TERMS:
            if " " in t:
                pytest.fail(f"Term has space (use underscore): {t!r}")


# ═══════════════════════════════════════════════════════════════
# MODALITY CONSTRAINTS
# ═══════════════════════════════════════════════════════════════

class TestModalityConstraints:
    def test_is_dict(self):
        assert isinstance(MODALITY_CONSTRAINTS, dict)

    def test_required_modalities_present(self):
        required = {"xray", "ct", "mri", "ekg", "labs", "ultrasound", "echo"}
        missing = required - set(MODALITY_CONSTRAINTS)
        assert not missing, f"Missing modalities: {missing}"

    def test_each_modality_has_forbidden_terms_key(self):
        for mod, data in MODALITY_CONSTRAINTS.items():
            assert "forbidden_terms" in data, f"Missing 'forbidden_terms' for {mod}"
            assert isinstance(data["forbidden_terms"], list), f"forbidden_terms not a list for {mod}"

    def test_each_modality_has_cannot_diagnose_key(self):
        for mod, data in MODALITY_CONSTRAINTS.items():
            assert "cannot_diagnose" in data, f"Missing 'cannot_diagnose' for {mod}"
            assert isinstance(data["cannot_diagnose"], list), f"cannot_diagnose not a list for {mod}"

    def test_xray_forbidden_terms_nonempty(self):
        assert len(MODALITY_CONSTRAINTS["xray"]["forbidden_terms"]) > 0

    def test_ct_forbidden_terms_empty(self):
        """CT has no forbidden terms — it can describe everything."""
        assert MODALITY_CONSTRAINTS["ct"]["forbidden_terms"] == []

    def test_xray_cannot_diagnose_matches_forbidden(self):
        """Terms in cannot_diagnose should also appear in forbidden_terms for xray."""
        forbidden = set(MODALITY_CONSTRAINTS["xray"]["forbidden_terms"])
        for term in MODALITY_CONSTRAINTS["xray"]["cannot_diagnose"]:
            assert term in forbidden, f"cannot_diagnose term {term!r} not in forbidden_terms"

    def test_no_empty_forbidden_terms_strings(self):
        for mod, data in MODALITY_CONSTRAINTS.items():
            for t in data["forbidden_terms"]:
                assert isinstance(t, str) and t.strip(), f"Empty/blank term in {mod} forbidden_terms"


# ═══════════════════════════════════════════════════════════════
# MODALITY_TERM_BLACKLIST — backward-compat alias
# ═══════════════════════════════════════════════════════════════

class TestModalityTermBlacklist:
    def test_is_dict(self):
        assert isinstance(MODALITY_TERM_BLACKLIST, dict)

    def test_keys_match_constraints(self):
        assert set(MODALITY_TERM_BLACKLIST.keys()) == set(MODALITY_CONSTRAINTS.keys())

    def test_values_match_forbidden_terms(self):
        for mod, terms in MODALITY_TERM_BLACKLIST.items():
            expected = MODALITY_CONSTRAINTS[mod]["forbidden_terms"]
            assert terms == expected, f"Mismatch for modality {mod}"

    def test_xray_blacklist_contains_hounsfield(self):
        assert "Hounsfield" in MODALITY_TERM_BLACKLIST["xray"]

    def test_ct_blacklist_is_empty(self):
        assert MODALITY_TERM_BLACKLIST["ct"] == []


# ═══════════════════════════════════════════════════════════════
# MEDICAL VOTE TERMS
# ═══════════════════════════════════════════════════════════════

class TestMedicalVoteTerms:
    def test_is_set(self):
        assert isinstance(MEDICAL_VOTE_TERMS, set)

    def test_non_empty(self):
        assert len(MEDICAL_VOTE_TERMS) > 0

    def test_critical_findings_present(self):
        critical = {"Pneumothorax", "Blutung", "Embolie", "Infarkt"}
        missing = critical - MEDICAL_VOTE_TERMS
        assert not missing, f"Missing critical findings: {missing}"

    def test_normal_findings_present(self):
        normal = {"unauffällig", "regelrecht"}
        missing = normal - MEDICAL_VOTE_TERMS
        assert not missing

    def test_ecg_terms_present(self):
        ecg = {"Vorhofflimmern", "Sinusrhythmus", "ST-Hebung"}
        missing = ecg - MEDICAL_VOTE_TERMS
        assert not missing

    def test_all_are_strings(self):
        for t in MEDICAL_VOTE_TERMS:
            assert isinstance(t, str) and t


# ═══════════════════════════════════════════════════════════════
# FINDING SEVERITY
# ═══════════════════════════════════════════════════════════════

class TestFindingSeverity:
    VALID_CERTAINTY = {"low", "medium", "high"}
    VALID_RISK = {"low", "moderate", "critical"}

    def test_is_dict(self):
        assert isinstance(FINDING_SEVERITY, dict)

    def test_non_empty(self):
        assert len(FINDING_SEVERITY) > 0

    def test_all_values_are_two_tuples(self):
        for term, val in FINDING_SEVERITY.items():
            assert isinstance(val, tuple) and len(val) == 2, f"Bad value for {term}: {val}"

    def test_certainty_values_valid(self):
        for term, (certainty, _) in FINDING_SEVERITY.items():
            assert certainty in self.VALID_CERTAINTY, \
                f"Invalid certainty {certainty!r} for {term}"

    def test_risk_values_valid(self):
        for term, (_, risk) in FINDING_SEVERITY.items():
            assert risk in self.VALID_RISK, \
                f"Invalid risk {risk!r} for {term}"

    def test_critical_findings_have_high_certainty(self):
        critical_terms = {"Pneumothorax", "Blutung", "Embolie", "Infarkt"}
        for t in critical_terms:
            if t in FINDING_SEVERITY:
                certainty, risk = FINDING_SEVERITY[t]
                assert certainty == "high", f"{t} should require high certainty"
                assert risk == "critical", f"{t} should be critical risk"


# ═══════════════════════════════════════════════════════════════
# LANGUAGE GATE
# ═══════════════════════════════════════════════════════════════

class TestLanguageGate:
    def test_is_dict(self):
        assert isinstance(LANGUAGE_GATE, dict)

    def test_non_empty(self):
        assert len(LANGUAGE_GATE) > 0

    def test_all_values_are_two_tuples(self):
        for phrase, val in LANGUAGE_GATE.items():
            assert isinstance(val, tuple) and len(val) == 2, f"Bad value for {phrase!r}"

    def test_thresholds_are_floats(self):
        for phrase, (replacement, threshold) in LANGUAGE_GATE.items():
            assert isinstance(threshold, float), f"Non-float threshold for {phrase!r}"

    def test_thresholds_are_in_range(self):
        """Threshold must be 0.0-1.0 OR >1.0 (the 'always replace' sentinel)."""
        for phrase, (replacement, threshold) in LANGUAGE_GATE.items():
            assert 0.0 <= threshold, f"Negative threshold for {phrase!r}"

    def test_replacements_are_non_empty_strings(self):
        for phrase, (replacement, _) in LANGUAGE_GATE.items():
            assert isinstance(replacement, str) and replacement.strip(), \
                f"Empty replacement for {phrase!r}"

    def test_always_replace_entries_have_threshold_above_one(self):
        """Entries with threshold > 1.0 are 'always replace' regardless of confidence."""
        always_phrases = {p for p, (_, t) in LANGUAGE_GATE.items() if t > 1.0}
        assert len(always_phrases) > 0, "Expected at least one 'always replace' entry"

    def test_definitive_phrase_present(self):
        assert "definitiv" in LANGUAGE_GATE


# ═══════════════════════════════════════════════════════════════
# FORBIDDEN PHRASES ALWAYS
# ═══════════════════════════════════════════════════════════════

class TestForbiddenPhrasesAlways:
    def test_is_list(self):
        assert isinstance(FORBIDDEN_PHRASES_ALWAYS, list)

    def test_non_empty(self):
        assert len(FORBIDDEN_PHRASES_ALWAYS) > 0

    def test_all_strings(self):
        for phrase in FORBIDDEN_PHRASES_ALWAYS:
            assert isinstance(phrase, str) and phrase

    def test_no_duplicates(self):
        assert len(FORBIDDEN_PHRASES_ALWAYS) == len(set(FORBIDDEN_PHRASES_ALWAYS))

    def test_absolute_certainty_phrase_present(self):
        assert any("absolut" in p.lower() for p in FORBIDDEN_PHRASES_ALWAYS)


# ═══════════════════════════════════════════════════════════════
# CATEGORY KEYWORDS
# ═══════════════════════════════════════════════════════════════

class TestCategoryKeywords:
    REQUIRED_TYPES = {"ECG", "XRay", "CT", "MRI", "Ultrasound", "BloodTest", "Echo"}

    def test_is_dict(self):
        assert isinstance(CATEGORY_KEYWORDS, dict)

    def test_required_report_types_present(self):
        missing = self.REQUIRED_TYPES - set(CATEGORY_KEYWORDS)
        assert not missing, f"Missing report types: {missing}"

    def test_all_keyword_lists_non_empty(self):
        for rtype, keywords in CATEGORY_KEYWORDS.items():
            assert len(keywords) >= 2, f"Too few keywords for {rtype}"

    def test_all_keywords_are_strings(self):
        for rtype, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                assert isinstance(kw, str) and kw, f"Bad keyword in {rtype}: {kw!r}"

    def test_ecg_has_ekg_keyword(self):
        assert "EKG" in CATEGORY_KEYWORDS["ECG"]

    def test_xray_has_thorax_keyword(self):
        assert "Thorax" in CATEGORY_KEYWORDS["XRay"]

    def test_ct_has_hounsfield_keyword(self):
        assert "Hounsfield" in CATEGORY_KEYWORDS["CT"]

    def test_echo_has_ejektionsfraktion(self):
        assert "Ejektionsfraktion" in CATEGORY_KEYWORDS["Echo"]


# ═══════════════════════════════════════════════════════════════
# CROSS-MODULE CONSISTENCY
# Verifies analyzer_prompts uses vocabulary values correctly.
# ═══════════════════════════════════════════════════════════════

class TestCrossModuleConsistency:
    def test_anatomy_terms_in_visibility_prompt(self):
        """All anatomy terms must appear in the VISIBILITY_USER prompt."""
        from services.analyzer_prompts import VISIBILITY_USER
        for term in ANATOMY_TERMS:
            assert term in VISIBILITY_USER, \
                f"Anatomy term {term!r} missing from VISIBILITY_USER"

    def test_modality_blacklist_matches_vocabulary(self):
        """MODALITY_TERM_BLACKLIST in analyzer_prompts must match findings_vocabulary."""
        from services.analyzer_prompts import MODALITY_TERM_BLACKLIST as prompts_blacklist
        for mod, expected_terms in MODALITY_TERM_BLACKLIST.items():
            actual_terms = prompts_blacklist.get(mod, [])
            assert actual_terms == expected_terms, \
                f"Blacklist mismatch for {mod}: expected {expected_terms}, got {actual_terms}"

    def test_vocabulary_has_no_package_imports(self):
        """findings_vocabulary.py must not import from the services package."""
        import ast
        vocab_path = os.path.join(os.path.dirname(__file__), "..", "services", "findings_vocabulary.py")
        source = open(vocab_path, encoding="utf-8").read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("services"):
                    pytest.fail(f"findings_vocabulary imports from services: {node.module}")
