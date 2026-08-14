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
SURFACES = ROOT / "model_trace" / "regulatory_source_surfaces.json"

SURFACE_REGISTRY_KEYS = {
    "ema_medicines_report": "ema_epar",
    "ema_orphan_designations_report": "ema_epar",
    "pmda_approved_products_page": "pmda_japan",
    "fda_orphan_search_page": "fda_orphan",
}


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
        "plain_status": "Source surface captured",
        "plain_use": "Bounds where orphan designation and exclusivity evidence would be checked.",
        "claim": "Official search page is captured and hashed; web-form result rows are not normalized here.",
    },
    "European Medicines Agency EPAR": {
        "region_or_scope": "Europe",
        "plain_status": "Small official workbooks captured",
        "plain_use": "Bounds European medicines and orphan-designation source surfaces.",
        "claim": "Official EMA workbooks are captured and hashed; not normalized into full cross-region coverage.",
    },
    "Japan PMDA drug approvals": {
        "region_or_scope": "Japan",
        "plain_status": "Source surface captured",
        "plain_use": "Bounds Japanese approved-product source location.",
        "claim": "Official PMDA approved-products page is captured and hashed; larger linked PDF is not vendored.",
    },
    "Convoke": {
        "region_or_scope": "Drug-program intelligence",
        "plain_status": "Listed, not incorporated",
        "plain_use": "Would join targets to drug programs if licensed access is available.",
        "claim": "Not admitted without documented access, license terms, and a replayable query receipt.",
    },
}


def main() -> None:
    surfaces = {}
    if SURFACES.exists():
        captured = json.loads(SURFACES.read_text())
        for item in captured.get("sources", []):
            registry_key = SURFACE_REGISTRY_KEYS.get(item["key"])
            if registry_key:
                surfaces.setdefault(registry_key, []).append(item)

    rows = []
    for r in registry_status():
        plain = PLAIN.get(r["name"], {})
        source_surface_count = len(surfaces.get(r["key"], []))
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
                "source_surface_count": source_surface_count,
            }
        )

    payload = {
        "schema": "protein_hinge.regulatory_coverage.v1",
        "status": "coverage_map_not_full_ingestion",
        "claim_boundary": "Regulatory search coverage, not legal advice and not a full global approved-drug database.",
        "plain_english": (
            "The MVP has U.S. trial evidence, selected U.S. FDA label/NDC evidence, "
            "Open Targets support, and small official EMA/PMDA/FDA-orphan source "
            "surfaces captured for traceability. It still does not claim a full "
            "FDA/EMA/PMDA approved-drug database."
        ),
        "active_dashboard_database": "db/biocustody.db and site/biocustody.db",
        "coverage": rows,
        "source_surfaces_path": "model_trace/regulatory_source_surfaces.json",
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    OUT.write_text(text)
    SITE_OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"wrote {SITE_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
