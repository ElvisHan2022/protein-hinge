#!/usr/bin/env python3
"""Deterministic GAP lane grading rules."""
from __future__ import annotations


CLAIM_CEILING = "REPURPOSING_HYPOTHESIS"
PROHIBITED_CLAIM = "THERAPEUTIC_RECOMMENDATION"

STAGE_ORDER = {
    "approved": 4,
    "phase 3": 3,
    "phase iii": 3,
    "phase 2": 2,
    "phase ii": 2,
    "phase 1/2": 1,
    "phase 1": 1,
    "phase i": 1,
    "preclinical": 0,
}


def refuse_claim(level: str) -> dict[str, str | bool]:
    if level == PROHIBITED_CLAIM:
        return {
            "emitted": False,
            "reason": "THERAPEUTIC_RECOMMENDATION cannot be emitted by this system.",
            "highest_level_available": CLAIM_CEILING,
        }
    return {"emitted": True, "level": level}


def grade_candidate(row: dict) -> dict[str, str]:
    """Apply first-match-wins GAP rules from docs/GAP_LANE_SPEC.md."""
    if row.get("target_reconcile") == "UNRESOLVED":
        return {"rule_fired": "G000_UNRESOLVED_TARGET", "grade": "ABSTAIN"}
    if not row.get("target_symbol") or float(row.get("association_score") or 0) <= 0:
        return {"rule_fired": "G001_NO_TARGET", "grade": "ABSTAIN"}
    if not row.get("drug_program"):
        return {"rule_fired": "G002_NO_PROGRAM", "grade": "ABSTAIN"}
    if row.get("lookup_failed"):
        return {"rule_fired": "G003_LOOKUP_FAILED", "grade": "ABSTAIN"}
    if int(row.get("n_trials") or 0) > 0 or row.get("prior_trials"):
        return {"rule_fired": "G004_ALREADY_TRIED", "grade": "NOT_A_GAP"}

    stage = str(row.get("stage") or "").strip().casefold()
    if stage == "approved":
        return {"rule_fired": "G005_GAP_APPROVED_DRUG", "grade": "GAP_HIGH"}
    if STAGE_ORDER.get(stage, -1) >= 2:
        return {"rule_fired": "G006_GAP_LATE_STAGE", "grade": "GAP_MEDIUM"}
    if STAGE_ORDER.get(stage, -1) >= 0:
        return {"rule_fired": "G007_GAP_EARLY", "grade": "GAP_LOW"}
    return {"rule_fired": "G008_UNCLASSIFIED", "grade": "ABSTAIN"}


def _self_test() -> None:
    cases = [
        ({"target_reconcile": "UNRESOLVED"}, "G000_UNRESOLVED_TARGET"),
        ({"target_symbol": "", "drug_program": "x"}, "G001_NO_TARGET"),
        ({"target_symbol": "TAZ", "association_score": 0.8}, "G002_NO_PROGRAM"),
        ({"target_symbol": "TAZ", "association_score": 0.8, "drug_program": "x", "lookup_failed": True}, "G003_LOOKUP_FAILED"),
        ({"target_symbol": "TAZ", "association_score": 0.8, "drug_program": "x", "n_trials": 1}, "G004_ALREADY_TRIED"),
        ({"target_symbol": "TAZ", "association_score": 0.8, "drug_program": "x", "stage": "Approved"}, "G005_GAP_APPROVED_DRUG"),
        ({"target_symbol": "TAZ", "association_score": 0.8, "drug_program": "x", "stage": "Phase 3"}, "G006_GAP_LATE_STAGE"),
        ({"target_symbol": "TAZ", "association_score": 0.8, "drug_program": "x", "stage": "Preclinical"}, "G007_GAP_EARLY"),
    ]
    for row, want in cases:
        got = grade_candidate(row)["rule_fired"]
        if got != want:
            raise SystemExit(f"{row}: got {got}, want {want}")
    refused = refuse_claim(PROHIBITED_CLAIM)
    if refused.get("emitted"):
        raise SystemExit("THERAPEUTIC_RECOMMENDATION refusal failed")
    print("rules self-test OK")


if __name__ == "__main__":
    _self_test()
