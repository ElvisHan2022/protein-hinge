#!/usr/bin/env python3
"""Build the ClinVar genetic-evidence subset for the eight consensus genes.

No AWS required. Queries NCBI ClinVar through E-utilities, writes:

  data/healthomics/clinvar_subset.tsv        the table HealthOmics will ingest
  data/healthomics/clinvar_provenance.json   query URLs + response digests
  site/assets/clinvar_evidence.json          per-gene projection for the dashboard

Every query URL and raw response digest is recorded, so the subset is
re-fetchable and checkable by a third party. The TSV is the exact object the
HealthOmics annotation store import consumes (scripts/setup_healthomics.py).

Claim boundary: ClinVar classifications are assertions by submitters, not
measured rescue and not diagnosis. The dashboard must render them as
"pathogenic variant reported" evidence only.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "healthomics"
SITE_ASSETS = ROOT / "site" / "assets"

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# The eight consensus knockouts (fcg/ingest.py). TAZ is HGNC TAFAZZIN.
GENES = ["TAFAZZIN", "CRLS1", "PGS1", "PTPMT1", "HADHA", "PHB", "PHB2", "CHCHD3"]
# ClinVar indexes the Barth gene under both symbols; TAFAZZIN is current HGNC.

PATHOGENIC = '("clinsig pathogenic"[Properties] OR "clinsig likely pathogenic"[Properties])'

# Large CNVs (whole-arm copy-number events) span hundreds of genes and would
# inflate per-gene counts with variants that are not gene-specific. A record
# is kept only if it is not a copy-number object and involves few genes.
MAX_GENES_PER_VARIANT = 3
CNV_OBJ_TYPES = ("copy number loss", "copy number gain")


def gene_specific(rec: dict) -> bool:
    obj_type = (rec.get("obj_type") or "").lower()
    if any(t in obj_type for t in CNV_OBJ_TYPES):
        return False
    return len(rec.get("genes") or []) <= MAX_GENES_PER_VARIANT


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "protein-hinge-demo/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SITE_ASSETS.mkdir(parents=True, exist_ok=True)

    provenance = {
        "schema": "protein_hinge.clinvar_subset.v1",
        "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": "NCBI ClinVar via E-utilities",
        "filter": "pathogenic OR likely pathogenic, per gene",
        "genes": GENES,
        "queries": [],
    }
    rows: list[dict] = []
    per_gene: dict[str, dict] = {}

    for gene in GENES:
        term = f"{gene}[gene] AND {PATHOGENIC}"
        search_url = f"{EUTILS}/esearch.fcgi?" + urllib.parse.urlencode({
            "db": "clinvar", "term": term, "retmax": "500", "retmode": "json",
        })
        raw = fetch(search_url)
        provenance["queries"].append({
            "gene": gene, "stage": "esearch", "url": search_url,
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
        })
        result = json.loads(raw)["esearchresult"]
        ids = result.get("idlist", [])
        total = int(result.get("count", "0"))
        kept = 0
        excluded_cnv = 0
        conditions: dict[str, int] = {}

        for i in range(0, len(ids), 100):
            chunk = ids[i:i + 100]
            summary_url = f"{EUTILS}/esummary.fcgi?" + urllib.parse.urlencode({
                "db": "clinvar", "id": ",".join(chunk), "retmode": "json",
            })
            raw = fetch(summary_url)
            provenance["queries"].append({
                "gene": gene, "stage": "esummary", "url": summary_url,
                "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            })
            summaries = json.loads(raw).get("result", {})
            for uid in chunk:
                rec = summaries.get(uid)
                if not rec:
                    continue
                if not gene_specific(rec):
                    excluded_cnv += 1
                    continue
                kept += 1
                classification = (rec.get("germline_classification") or {})
                traits = []
                for ts in (rec.get("germline_classification") or {}).get("trait_set", []):
                    name = ts.get("trait_name")
                    if name and name not in ("not provided", "not specified"):
                        traits.append(name)
                        conditions[name] = conditions.get(name, 0) + 1
                rows.append({
                    "gene": gene,
                    "accession": rec.get("accession", ""),
                    "title": rec.get("title", ""),
                    "classification": classification.get("description", ""),
                    "review_status": classification.get("review_status", ""),
                    "conditions": "; ".join(sorted(set(traits))[:6]),
                })
            time.sleep(0.4)  # E-utilities courtesy limit, no API key

        top = sorted(conditions.items(), key=lambda kv: -kv[1])[:5]
        per_gene[gene] = {
            "pathogenic_or_likely": kept,
            "records_fetched": len(ids),
            "clinvar_total_before_filter": total,
            "excluded_large_cnv": excluded_cnv,
            "top_conditions": [{"condition": c, "records": n} for c, n in top],
        }
        time.sleep(0.4)

    tsv_path = OUT_DIR / "clinvar_subset.tsv"
    cols = ["gene", "accession", "title", "classification", "review_status", "conditions"]
    with tsv_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(cols) + "\n")
        for r in rows:
            f.write("\t".join(str(r[c]).replace("\t", " ").replace("\n", " ") for c in cols) + "\n")
    tsv_digest = hashlib.sha256(tsv_path.read_bytes()).hexdigest()
    provenance["tsv"] = {"path": "data/healthomics/clinvar_subset.tsv",
                         "sha256": tsv_digest, "rows": len(rows)}
    (OUT_DIR / "clinvar_provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n")

    evidence = {
        "schema": "protein_hinge.clinvar_evidence.v1",
        "captured_at": provenance["captured_at"],
        "claim_boundary": "PATHOGENIC_VARIANT_REPORTED",
        "note": ("Counts are ClinVar submitter classifications (pathogenic or likely "
                 "pathogenic), fetched live from NCBI and re-fetchable from the recorded "
                 "query URLs. Large copy-number events spanning many genes are excluded, "
                 "so each count reflects gene-specific variants only; the excluded totals "
                 "are recorded per gene. This is genetic association evidence, not "
                 "measured rescue and not diagnosis."),
        "tsv_sha256": tsv_digest,
        "genes": [{"gene": g, **per_gene[g]} for g in GENES],
    }
    (SITE_ASSETS / "clinvar_evidence.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n")

    print(f"rows {len(rows)}")
    print(f"tsv  {tsv_path.relative_to(ROOT)}  sha256 {tsv_digest[:16]}…")
    print("wrote site/assets/clinvar_evidence.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
