#!/usr/bin/env python3
"""Build the small prescripted GAP lane run artifacts for the demo."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from pathlib import Path

from normalize import reconcile
from rules import CLAIM_CEILING, grade_candidate, refuse_claim


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
RUN = HERE / "runs" / "2026-08-13"


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else ["empty"]
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def build_rows() -> list[dict]:
    src = json.loads((HERE / "elvis_prescripted_demo.json").read_text())
    out = []
    for row in src["rows"]:
        trials = [x.strip() for x in str(row.get("prior_trials") or "").split(";") if x.strip()]
        reconciled = reconcile(row.get("target_symbol", ""), row.get("target_symbol", ""))
        base = {
            "disease": row["disease"],
            "target_symbol": row.get("target_symbol", ""),
            "target_reconcile": reconciled["outcome"],
            "alias_used": reconciled["alias_used"],
            "association_score": row.get("association_score") or 0,
            "drug_program": row.get("drug_program", ""),
            "company": row.get("company", ""),
            "modality": row.get("modality", ""),
            "stage": row.get("stage", ""),
            "prior_trials": ";".join(trials),
            "n_trials": len(trials),
            "lookup_failed": False,
        }
        base.update(grade_candidate(base))
        out.append(base)
    return out


def merkle_root(items: list[str]) -> str:
    leaves = [bytes.fromhex(x.replace("sha256:", "")) for x in sorted(items)]
    if not leaves:
        return sha256_bytes(b"")
    while len(leaves) > 1:
        nxt = []
        for i in range(0, len(leaves), 2):
            right = leaves[i + 1] if i + 1 < len(leaves) else leaves[i]
            nxt.append(hashlib.sha256(b"\x01" + leaves[i] + right).digest())
        leaves = nxt
    return "sha256:" + leaves[0].hex()


def main() -> None:
    RUN.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    write_csv(RUN / "candidates.csv", rows)
    write_csv(RUN / "targets.csv", [
        {
            "disease_id": "MONDO:0010526",
            "disease": "Barth syndrome",
            "ensembl_id": "ENSG00000102125",
            "symbol": "TAZ",
            "score": 0.89,
            "tractability_buckets": 0,
            "source": "prescripted_validation_case",
        }
    ])
    write_csv(RUN / "programs.csv", [
        {
            "program": "elamipretide",
            "company": "Stealth BioTherapeutics",
            "modality": "peptide",
            "target_raw": "TAZ/cardiolipin module",
            "target_symbol": "TAZ",
            "stage": "Approved",
            "source": "Elvis handoff Appendix A",
        }
    ])
    write_csv(RUN / "priors.csv", [
        {
            "disease_id": "MONDO:0010526",
            "disease": "Barth syndrome",
            "drug": "elamipretide",
            "nct_ids": "NCT03098797;NCT07531251;NCT04689360",
            "n_trials": 3,
            "caveat": "ClinicalTrials.gov registers trials rather than programs, so absence of a registered competitor is weak evidence of no competitor.",
        }
    ])
    abstentions = {
        "diseases_with_no_target_above_threshold": 0,
        "targets_whose_names_did_not_reconcile": 0,
        "lookups_that_failed": 0,
        "reasons": [],
    }
    (RUN / "abstentions.json").write_text(json.dumps(abstentions, indent=2, sort_keys=True) + "\n")

    files = ["targets.csv", "programs.csv", "priors.csv", "candidates.csv", "abstentions.json"]
    digests = {name: sha256_file(RUN / name) for name in files}
    receipt = {
        "schema": "protein_hinge.gap.receipt.v1",
        "lane": "gap",
        "run_date": str(date(2026, 8, 13)),
        "claim_ceiling": CLAIM_CEILING,
        "therapeutic_recommendation_refusal": refuse_claim("THERAPEUTIC_RECOMMENDATION"),
        "source_spec": "docs/GAP_LANE_SPEC.md",
        "source_spec_sha256": sha256_file(ROOT / "docs" / "GAP_LANE_SPEC.md"),
        "files": digests,
        "merkle_convention": "duplicate-last/sha256-over-file-digests",
        "merkle_root": merkle_root(list(digests.values())),
        "note": "Prescripted validation lane. Live Convoke/Open Targets joins remain explicit unblocks.",
    }
    (RUN / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    (HERE / "latest.json").write_text(json.dumps({"run_id": "2026-08-13", "path": str(RUN.relative_to(ROOT))}, indent=2) + "\n")
    print(f"wrote {RUN.relative_to(ROOT)}")
    print(f"gap root {receipt['merkle_root']}")


if __name__ == "__main__":
    main()
