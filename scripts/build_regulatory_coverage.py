#!/usr/bin/env python3
"""Build the plain regulatory coverage receipt used by the demo UI."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "fto"))

from fto import registry_status  # noqa: E402

OUT = ROOT / "model_trace" / "regulatory_coverage.json"
SITE_OUT = ROOT / "site" / "assets" / "regulatory_coverage.json"


PLAIN = {
    "ClinicalTrials.gov": {
        "region_or_scope": "United States / international trial registry",
        "plain_status": "Incorporated",
        "plain_use": "Checks whether this disease and program have already appeared together in registered studies.",
        "claim": "Trial-search evidence only; absence of a trial is not proof that no program exists.",
    },
    "openFDA drug endpoints": {
        "region_or_scope": "United States",
        "plain_status": "Partially incorporated",
        "plain_use": "Pins the incumbent elamipretide label and NDC records.",
        "claim": "Specific incumbent-label evidence; not a full FDA approved-drug census.",
    },
    "Open Targets Platform": {
        "region_or_scope": "Global public target evidence",
        "plain_status": "Incorporated",
        "plain_use": "Checks tractability and drug/clinical-candidate counts for selected targets.",
        "claim": "Target-evidence support only; not a regulatory approval source.",
    },
    "FDA Orphan Drug Product designation database": {
        "region_or_scope": "United States",
        "plain_status": "Listed, not incorporated",
        "plain_use": "Would bound orphan designation and exclusivity questions.",
        "claim": "Not admitted because the current public query surface is a web form, not a stable replayable API.",
    },
    "European Medicines Agency EPAR": {
        "region_or_scope": "Europe",
        "plain_status": "Listed, not incorporated",
        "plain_use": "Would bound European authorization status.",
        "claim": "Future work until the query surface, corpus date, fields, and reuse terms are documented.",
    },
    "Japan PMDA drug approvals": {
        "region_or_scope": "Japan",
        "plain_status": "Listed, not incorporated",
        "plain_use": "Would bound Japanese approval status.",
        "claim": "Future work until the query surface, corpus date, fields, and reuse terms are documented.",
    },
    "Convoke": {
        "region_or_scope": "Drug-program intelligence",
        "plain_status": "Listed, not incorporated",
        "plain_use": "Would join targets to drug programs if licensed access is available.",
        "claim": "Not admitted without documented access, license terms, and a replayable query receipt.",
    },
}


def main() -> None:
    rows = []
    for r in registry_status():
        plain = PLAIN.get(r["name"], {})
        rows.append(
            {
                "registry_key": r["key"],
                "name": r["name"],
                "lane": r["lane"],
                "wired": bool(r["wired"]),
                "region_or_scope": plain.get("region_or_scope", "Other"),
                "plain_status": plain.get(
                    "plain_status",
                    "Incorporated" if r["wired"] else "Listed, not incorporated",
                ),
                "plain_use": plain.get("plain_use", ""),
                "claim": plain.get("claim", ""),
                "blocker": r.get("blocker"),
            }
        )

    payload = {
        "schema": "protein_hinge.regulatory_coverage.v1",
        "status": "coverage_map_not_full_ingestion",
        "claim_boundary": "Regulatory search coverage, not legal advice and not a full global approved-drug database.",
        "plain_english": (
            "The MVP has U.S. trial evidence, selected U.S. FDA label/NDC evidence, "
            "and Open Targets support. Europe, Japan, FDA orphan designation, "
            "Convoke, and comprehensive approved-drug coverage are listed as future work."
        ),
        "active_dashboard_database": "db/biocustody.db and site/biocustody.db",
        "coverage": rows,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    OUT.write_text(text)
    SITE_OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"wrote {SITE_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
