"""
Validate the full analyzer pipeline end-to-end.
Since the deployed server's OpenRouter models are returning errors,
we validate the pipeline logic directly via the existing unit tests
plus a comprehensive mock-based validation that exercises every pipeline step.

This verifies:
  - Pipeline logic correctness
  - Risk classification formula
  - Strict CSM decision logic
  - All three validators (JSON schema, canonical vocab, consistency)
  - Explainability log structure
  - Language normalization
  - Modality validation
  - Model voting / agreement computation
  - Clinical safety mode activation
  - Human review triggering

Runs in < 1 second, no server needed.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.analyzer_prompts import (
    apply_confidence_gate,
    normalize_clinical_language,
    validate_modality_output,
    classify_risk,
    should_trigger_human_review,
    should_use_clinical_safety_mode,
    apply_clinical_safety_mode,
    should_trigger_strict_csm,
    apply_strict_clinical_safety_mode,
    build_strict_csm_log_entry,
    compute_model_agreement,
    build_pipeline_explainability_log,
    validate_json_schema,
    validate_canonical_vocabulary,
    check_json_narrative_consistency,
    build_safety_layer_from_visibility,
)

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS [{name}]")
    else:
        FAIL += 1
        print(f"  FAIL [{name}] {detail}")

print("=" * 65)
print("COMPREHENSIVE PIPELINE LOGIC VALIDATION")
print("=" * 65)

# ── 1. Confidence Gate ──
print("\n[1] Confidence Gate")
check("full_at_0.85", apply_confidence_gate("test", 0.85) == "test")
check("full_at_0.99", "test" in apply_confidence_gate("test (85%)", 0.90))
check("strips_pct_at_0.72", "(85%)" not in apply_confidence_gate("risk (85%)", 0.72))
check("strips_all_pct_at_0.60", "80%" not in apply_confidence_gate("risk 80%", 0.60))
check("safe_minimal_at_0.40", "Konfidenz" in apply_confidence_gate("maligner Tumor", 0.40))
check("empty_no_crash_at_low_conf", len(apply_confidence_gate("", 0.50)) > 0)  # adds confidence notice even on empty
check("zero_conf", isinstance(apply_confidence_gate("text", 0.0), str))

# ── 2. Language Normalization ──
print("\n[2] Language Normalization")
txt, ch = normalize_clinical_language("Normal text", 0.90)
check("safe_text_no_changes", ch == [])
txt, ch = normalize_clinical_language("absolut sicher ein Infarkt", 0.99)
check("always_forbidden_replaced", "absolut sicher" not in txt.lower())
txt, ch = normalize_clinical_language("Definitiv eine Pneumonie", 0.60)
check("low_conf_replaces_definitiv", "definitiv" not in txt.lower() and len(ch) > 0)
txt, ch = normalize_clinical_language("Definitiv eine Pneumonie", 0.90)
check("high_conf_keeps_definitiv", "definitiv" in txt.lower() and ch == [])
txt, ch = normalize_clinical_language("", 0.72)
check("empty_no_crash", txt == "" and ch == [])

# ── 3. Modality Validation ──
print("\n[3] Modality Validation")
txt, v = validate_modality_output("Normal chest X-ray finding", "xray")
check("clean_xray_no_violations", v == [])
txt, v = validate_modality_output("Hounsfield value 45 HU", "xray")
check("hounsfield_in_xray_violation", len(v) > 0)
txt, v = validate_modality_output("Hounsfield value 45 HU", "ct")
check("hounsfield_in_ct_ok", v == [])
txt, v = validate_modality_output("Lungenembolie", "xray")
check("embolie_in_xray_violation", any("lungenembolie" in x.lower() for x in v))
txt, v = validate_modality_output("Lungenembolie", "ct")
check("embolie_in_ct_ok", v == [])
txt, v = validate_modality_output("text", "")
check("empty_modality_ok", isinstance(v, list))

# ── 4. Risk Classification ──
print("\n[4] Risk Classification")
vis_good = {"image_quality": "good", "visible": ["thorax"], "partial": [], "hidden": []}
vis_poor = {"image_quality": "poor", "visible": [], "partial": ["thorax"], "hidden": ["lungs", "heart"]}
voting_ok = {"disagreement": False, "agreement_score": 1.0}
voting_bad = {"disagreement": True, "agreement_score": 0.3}

r1 = classify_risk([], vis_good, 0.85, None, voting_ok)
check("clean_is_low_risk", r1["level"] == "low_risk")
check("clean_has_reasons_list", isinstance(r1["reasons"], list))

r2 = classify_risk(["Hounsfield", "axiale Schicht"], vis_poor, 0.40, None, voting_bad)
check("bad_input_high_risk", r2["level"] in ("dangerous", "critical_review_required"))
check("risk_has_score", isinstance(r2["score"], int) and 0 <= r2["score"] <= 100)

r_poor = classify_risk([], vis_poor, 0.85, None, voting_ok)
r_good = classify_risk([], vis_good, 0.85, None, voting_ok)
check("poor_quality_higher_risk", r_poor["score"] > r_good["score"])

r_low_conf = classify_risk([], vis_good, 0.40, None, voting_ok)
check("low_conf_higher_risk", r_low_conf["score"] > r_good["score"])

r_multi_viol = classify_risk(["a", "b", "c"], vis_good, 0.85, None, voting_ok)
check("violations_increase_risk", r_multi_viol["score"] > r_good["score"])

structured_with_risky = {"visible_regions": [], "visible_findings": [], "uncertain_findings": ["Metastase verdacht"], "limitations": [], "forbidden_sections_skipped": []}
r_risky_finding = classify_risk([], vis_good, 0.85, structured_with_risky, voting_ok)
check("risky_terms_increase_risk", r_risky_finding["score"] > r_good["score"])

# ── 5. Human Review ──
print("\n[5] Human Review")
tr, _ = should_trigger_human_review("low_risk", 0.85, [], vis_good, voting_ok)
check("clean_no_review", tr is False)
tr, _ = should_trigger_human_review("dangerous", 0.85, [], vis_good, voting_ok)
check("dangerous_triggers_review", tr is True)
tr, _ = should_trigger_human_review("critical_review_required", 0.85, [], vis_good, voting_ok)
check("critical_triggers_review", tr is True)
tr, banner = should_trigger_human_review("moderate_risk", 0.85, [], vis_good, voting_ok)
check("moderate_triggers_review", tr is True)
check("banner_nonempty_when_triggered", len(banner) > 0)
tr, _ = should_trigger_human_review("low_risk", 0.40, [], vis_good, voting_ok)
check("low_conf_triggers_review", tr is True)
tr, _ = should_trigger_human_review("low_risk", 0.85, ["a", "b"], vis_good, voting_ok)
check("violations_trigger_review", tr is True)

# ── 6. Clinical Safety Mode ──
print("\n[6] Clinical Safety Mode")
risk_ok = {"level": "low_risk", "score": 10, "reasons": []}
risk_bad = {"level": "dangerous", "score": 90, "reasons": ["critical"]}
act, _ = should_use_clinical_safety_mode(risk_ok, vis_good, voting_ok)
check("safe_no_activation", act is False)
act, _ = should_use_clinical_safety_mode(risk_bad, vis_good, voting_ok)
check("dangerous_activates_csm", act is True)
act, _ = should_use_clinical_safety_mode(risk_bad, vis_poor, voting_bad)
check("multiple_signals_activate_csm", act is True)

report_with_sections = (
    "## Befunde\nKein Nachweis eines Pneumothorax.\n\n"
    "## Interpretation\nDer Befund ist regelrecht.\n\n"
    "## Differentialdiagnosen\nKeine relevanten."
)
result, applied = apply_clinical_safety_mode(report_with_sections)
check("strips_interpretation", "## Interpretation" not in result)
check("strips_differentials", "## Differentialdiagnosen" not in result)
check("preserves_befunde", "Kein Nachweis eines Pneumothorax" in result)
check("applied_flag_true", applied is True)
result2, applied2 = apply_clinical_safety_mode("Simple normal text.")
check("no_sections_no_change", applied2 is False)

# ── 7. Strict CSM ──
print("\n[7] Strict CSM")
act, reason = should_trigger_strict_csm(voting_ok, vis_good, risk_ok, [], 0.85)
check("clean_no_strict", act is False)
act, reason = should_trigger_strict_csm(voting_bad, vis_good, risk_ok, [], 0.85)
check("disagreement_triggers_strict", act is True)
act, reason = should_trigger_strict_csm(voting_ok, {"image_quality": "poor", "hidden": ["a", "b"], "visible": [], "partial": []}, risk_ok, [], 0.85)
check("poor_quality_triggers_strict", act is True)
act, reason = should_trigger_strict_csm(voting_ok, vis_good, {"level": "dangerous", "score": 90, "reasons": ["x"]}, [], 0.85)
check("dangerous_triggers_strict", act is True)
act, reason = should_trigger_strict_csm(voting_ok, vis_good, risk_ok, ["a", "b"], 0.85)
check("violations_triggers_strict", act is True)
act, reason = should_trigger_strict_csm(voting_ok, vis_good, risk_ok, [], 0.50)
check("low_conf_triggers_strict", act is True)

safe_test = "## Befund\nNormal\n## Differentialdiagnose\nSomething\n## Interpretation\nMaybe\n## Beurteilung\nOK"
result_s, modified = apply_strict_clinical_safety_mode(safe_test)
check("strict_strips_differentials", "## Differentialdiagnose" not in result_s)  # section header stripped, word may appear in banner
check("strict_strips_interpretation", "## Interpretation" not in result_s)
check("strict_keeps_befund", "Befund" in result_s)
check("strict_adds_banner", "SICHERHEITSMODUS" in result_s)
check("strict_modifies", modified is True)

log = build_strict_csm_log_entry(True, "test reason", True, 100, 50)
check("strict_log_has_keys", all(k in log for k in ("step", "activated", "reason", "was_modified", "chars_before", "chars_after")))

# ── 8. JSON Schema Validation ──
print("\n[8] JSON Schema Validation")
result = validate_json_schema(None)
check("none_json_invalid", result["valid"] is False and len(result["errors"]) > 0)
result = validate_json_schema({"visible_regions": [], "partial_regions": [], "visible_findings": [], "uncertain_findings": [], "limitations": [], "forbidden_sections_skipped": []})
check("empty_but_valid_schema", result["schema_ok"] is True)
result = validate_json_schema({"visible_regions": ["thorax"], "partial_regions": [], "visible_findings": ["normal"], "uncertain_findings": [], "limitations": [], "forbidden_sections_skipped": []})
check("valid_json_schema", result["valid"] is True and result["schema_ok"] is True)
result = validate_json_schema({"visible_regions": "not_a_list", "partial_regions": [], "visible_findings": [], "uncertain_findings": [], "limitations": [], "forbidden_sections_skipped": []})
check("wrong_type_invalid", result["valid"] is False)
result = validate_json_schema({"visible_regions": [], "partial_regions": [], "visible_findings": [], "uncertain_findings": [], "limitations": [], "forbidden_sections_skipped": [], "image_quality": "poor"})
check("valid_quality_accepted", result["quality_ok"] is True)
result = validate_json_schema({"visible_regions": [], "partial_regions": [], "visible_findings": [], "uncertain_findings": [], "limitations": [], "forbidden_sections_skipped": [], "image_quality": "invalid_value"})
check("invalid_quality_rejected", result["quality_ok"] is False)

# ── 9. Canonical Vocabulary ──
print("\n[9] Canonical Vocabulary Validation")
valid_json = {"visible_regions": ["thorax", "lungen"], "partial_regions": [], "visible_findings": ["normalbefund"], "uncertain_findings": [], "limitations": [], "forbidden_sections_skipped": []}
result = validate_canonical_vocabulary(valid_json, "xray")
check("valid_vocab_passes", result["valid"] is True)
check("canonical_ratio_1.0", result["canonical_ratio"] == 1.0)

invalid_json = {"visible_regions": ["xyz_nonexistent_123"], "partial_regions": [], "visible_findings": ["some_made_up_term"], "uncertain_findings": [], "limitations": [], "forbidden_sections_skipped": []}
result = validate_canonical_vocabulary(invalid_json, "xray")
check("invalid_vocab_fails", result["valid"] is False)
check("unknown_terms_found", len(result["unknown_terms"]) > 0)
check("canonical_ratio_below_1", result["canonical_ratio"] < 1.0)
result = validate_canonical_vocabulary(None, "xray")
check("none_vocab_fails", result["valid"] is False)

# ── 10. Narrative Consistency ──
print("\n[10] Narrative Consistency")
result = check_json_narrative_consistency(valid_json, "Kein Nachweis einer Pneumonie. Normalbefund.")
check("narrative_terms_found", len(result.get("narrative_only_findings", [])) > 0)  # "Pneumonie" extracted from narrative
check("correctly_reports_findings", "narrative_only_findings" in result)

result = check_json_narrative_consistency(None, "Metastase im Gehirn gefunden.")
check("no_json_with_danger_terms", result["consistent"] is False and result["json_empty_narrative_full"] is True)

result = check_json_narrative_consistency(valid_json, "")
check("empty_narrative", result["consistent"] is True)
result = check_json_narrative_consistency({"visible_regions": [], "visible_findings": [], "uncertain_findings": [], "limitations": [], "forbidden_sections_skipped": [], "partial_regions": []}, "Patient hat Fieber und Husten. Pneumonie besteht.")
check("json_empty_narrative_full_flag", result["json_empty_narrative_full"] is True)

result = check_json_narrative_consistency(None, "Some text")
check("no_json_safe_text", result["consistent"] is True)

# ── 11. Model Voting ──
print("\n[11] Model Voting")
pneumonia = "Infiltrat im linken Unterlappen. Verdacht auf Pneumonie. Pleuraerguss links nicht ausgeschlossen."
normal = "Kein Nachweis eines Infiltrats. Unauffälliger Thoraxbefund. Lunge beidseits regelrecht belüftet."
v1 = compute_model_agreement([pneumonia])
check("single_model_no_disagreement", v1.get("disagreement") is False)
v2 = compute_model_agreement([pneumonia, pneumonia])
check("identical_no_disagreement", v2.get("disagreement") is False)
v3 = compute_model_agreement([pneumonia, normal])
check("contradictory_show_disagreement", v3.get("disagreement") is True)
check("agreement_float", isinstance(v3.get("agreement_score"), float))
v4 = compute_model_agreement([])
check("empty_no_crash", isinstance(v4, dict))
v5 = compute_model_agreement([None, pneumonia])
check("none_filtered", isinstance(v5, dict))

# ── 12. Explainability Log ──
print("\n[12] Explainability Log")
log_inputs = {
    "confidence": 0.85, "violations": [], "lang_changes": [],
    "risk_result": {"level": "low_risk", "score": 10, "reasons": []},
    "voting_result": {"disagreement": False, "agreement_score": 1.0},
    "visibility_data": {"image_quality": "good", "hidden": [], "partial": []},
    "clinical_safety_mode": False,
}
log = build_pipeline_explainability_log(**log_inputs)
check("returns_list", isinstance(log, list))
if log:
    check("entries_have_keys", all(k in log[0] for k in ("step", "reason", "action", "detail")))

log_inputs["violations"] = ["Hounsfield"]
log_inputs["lang_changes"] = ["definitiv -> moglicherweise"]
log_inputs["confidence"] = 0.55
log_inputs["clinical_safety_mode"] = True
log_inputs["risk_result"] = {"level": "dangerous", "score": 90, "reasons": ["critical"]}
log_inputs["voting_result"] = {"disagreement": True, "agreement_score": 0.3}
log2 = build_pipeline_explainability_log(**log_inputs)
check("longer_log_for_dangerous", len(log2) >= 4)

# ── 13. Safety Layer ──
print("\n[13] Safety Layer from Visibility")
sl = build_safety_layer_from_visibility({"visible": ["thorax"], "partial": [], "hidden": [], "image_quality": "good"})
check("no_hidden_returns_none", sl is None)
sl = build_safety_layer_from_visibility({"visible": ["thorax"], "partial": ["abdomen"], "hidden": ["brain"], "image_quality": "limited"})
check("hidden_creates_layer", sl is not None)
check("layer_has_forbidden", "forbidden_assessment" in sl)
check("layer_has_partial", "partial_regions" in sl)

# ── SUMMARY ──
print("\n" + "=" * 65)
print(f"RESULTS: {PASS} passed, {FAIL} failed out of {PASS + FAIL} checks")
if FAIL == 0:
    print("ALL PIPELINE LOGIC CHECKS PASSED")
else:
    print(f"WARNING: {FAIL} check(s) FAILED")
print("=" * 65)

sys.exit(0 if FAIL == 0 else 1)
