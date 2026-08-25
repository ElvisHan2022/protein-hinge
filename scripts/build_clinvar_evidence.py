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


# E-utilities throttles sustained bursts even below its documented 3 req/s,
# and answers a throttled request with HTTP 200 and a body carrying no
# "result" key. Backoff has to outlast the throttle window, so it is measured
# in tens of seconds, not seconds.
RETRY_WAITS = (2, 5, 15, 30)


def fetch_summaries(url: str, waits=RETRY_WAITS):
    """Return (summaries, raw, note).

    Treating a throttled response as an empty page silently discards every
    record in the batch. Retry with generous backoff and, if it still fails,
    hand back a note the caller must record as an abstention.
    """
    raw = b""
    note = "not attempted"
    for attempt, wait in enumerate(waits):
        try:
            raw = fetch(url)
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            note = f"undecodable response: {exc}"
        except Exception as exc:  # transient HTTP/network failure
            note = f"{type(exc).__name__}: {exc}"
        else:
            result = payload.get("result")
            if isinstance(result, dict) and result:
                return result, raw, None
            note = str((payload.get("eutilsresult") or {}).get("ERROR")
                       or payload.get("error") or payload.get("esummaryresult")
                       or "response carried no result payload")
        if attempt < len(waits) - 1:
            time.sleep(wait)
    return {}, raw, f"no usable summaries after {len(waits)} attempts: {note}"


def collect_summaries(ids, gene, provenance, batch_failures):
    """Return {uid: record} for these ids, splitting the batch when needed.

    E-utilities refuses to convert a response over 10 MB to JSON, and a few
    ClinVar records are enormous (a single copy-number entry can list over a
    thousand genes). One such record used to take its entire 100-id batch with
    it, silently. Splitting on failure isolates the oversized record instead of
    losing its neighbours; only a single id that still fails is unrecoverable,
    and that one is recorded as an abstention.
    """
    if not ids:
        return {}
    url = f"{EUTILS}/esummary.fcgi?" + urllib.parse.urlencode({
        "db": "clinvar", "id": ",".join(ids), "retmode": "json",
    })
    summaries, raw, note = fetch_summaries(url)
    provenance["queries"].append({
        "gene": gene, "stage": "esummary", "ids": len(ids), "url": url,
        "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
        **({"failed": note} if note else {}),
    })
    if summaries:
        return summaries
    if len(ids) == 1:
        batch_failures.append({"gene": gene, "ids": 1, "uid": ids[0],
                               "reason": note, "recoverable": False})
        return {}
    batch_failures.append({"gene": gene, "ids": len(ids), "reason": note,
                           "recoverable": True, "action": "split and retried"})
    mid = len(ids) // 2
    time.sleep(0.5)
    left = collect_summaries(ids[:mid], gene, provenance, batch_failures)
    time.sleep(0.5)
    right = collect_summaries(ids[mid:], gene, provenance, batch_failures)
    return {**left, **right}


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
    batch_failures: list[dict] = []

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
        no_summary = 0
        conditions: dict[str, int] = {}

        for i in range(0, len(ids), 100):
            chunk = ids[i:i + 100]
            summary_url = f"{EUTILS}/esummary.fcgi?" + urllib.parse.urlencode({
                "db": "clinvar", "id": ",".join(chunk), "retmode": "json",
            })
            summaries = collect_summaries(chunk, gene, provenance, batch_failures)
            for uid in chunk:
                rec = summaries.get(uid)
                if not rec:
                    no_summary += 1
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
            time.sleep(0.5)  # E-utilities courtesy limit, no API key

        top = sorted(conditions.items(), key=lambda kv: -kv[1])[:5]
        per_gene[gene] = {
            "pathogenic_or_likely": kept,
            "records_fetched": len(ids),
            "clinvar_total_before_filter": total,
            "excluded_large_cnv": excluded_cnv,
            "no_summary_returned": no_summary,
            "top_conditions": [{"condition": c, "records": n} for c, n in top],
        }
        time.sleep(0.4)

    tsv_path = OUT_DIR / "clinvar_subset.tsv"
    cols = ["gene", "accession", "title", "classification", "review_status", "conditions"]
    with tsv_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(cols) + "\n")
        for r in rows:
            f.write("\t".join(str(r[c]).replace("\t", " ").replace("\n", " ") for c in cols) + "\n")
    # Reconciliation: every fetched id must land in exactly one bucket.
    fetched = sum(g["records_fetched"] for g in per_gene.values())
    accounted = sum(g["pathogenic_or_likely"] + g["excluded_large_cnv"]
                    + g["no_summary_returned"] for g in per_gene.values())
    provenance["reconciliation"] = {
        "ids_fetched": fetched,
        "kept": sum(g["pathogenic_or_likely"] for g in per_gene.values()),
        "excluded_large_cnv": sum(g["excluded_large_cnv"] for g in per_gene.values()),
        "no_summary_returned": sum(g["no_summary_returned"] for g in per_gene.values()),
        "accounted": accounted,
        "balanced": fetched == accounted,
        "batch_failures": batch_failures,
    }

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
        "reconciliation": provenance["reconciliation"],
        "genes": [{"gene": g, **per_gene[g]} for g in GENES],
    }
    (SITE_ASSETS / "clinvar_evidence.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n")

    print(f"rows {len(rows)}")
    print(f"reconciliation: {fetched} fetched = {accounted} accounted "
          f"({'BALANCED' if fetched == accounted else 'UNBALANCED'})")
    print(f"tsv  {tsv_path.relative_to(ROOT)}  sha256 {tsv_digest[:16]}…")
    print("wrote site/assets/clinvar_evidence.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
