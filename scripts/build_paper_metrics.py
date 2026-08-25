#!/usr/bin/env python3
"""Regenerate every number the paper cites, from the artifacts on disk.

The paper's claim is that enforced verification prevents silent errors. That
claim is only as good as its arithmetic, so no number in the paper should be
typed by hand. This script derives them all from the lane outputs and writes:

  model_trace/paper_metrics.json   machine-readable, with corpus digests
  docs/PAPER_METRICS.md            the table, ready to paste

Run it after any lane rebuild. If a number in the paper disagrees with this
file, this file is right and the paper is stale.

The ablation compares two pipelines over identical inputs:

  enforcement ON   what this system does
  enforcement OFF  the same pipeline with one guard removed -- the
                   implementation you get by following each source's
                   documentation without anticipating the failure

A *silent* error is wrong, well-formed, raises nothing, and is
indistinguishable downstream from a correct result. Loud failures (a crash, a
bounds error) are excluded from the numerator: they are not the problem.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "model_trace" / "paper_metrics.json"
OUT_MD = ROOT / "docs" / "PAPER_METRICS.md"


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def digest(rel: str) -> str:
    p = ROOT / rel
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


def main() -> int:
    clinvar = load("site/assets/clinvar_evidence.json")
    fasta = load("site/assets/fasta_lane.json")
    prov = load("data/healthomics/clinvar_provenance.json")
    recon = prov.get("reconciliation", {})

    # ---- G2: copy-number exclusion -----------------------------------
    genes = clinvar["genes"]
    kept = sum(g["pathogenic_or_likely"] for g in genes)
    excluded = sum(g["excluded_large_cnv"] for g in genes)
    naive_total = kept + excluded          # what an unfiltered pipeline counts
    zeroed = [g["gene"] for g in genes
              if g["pathogenic_or_likely"] == 0 and g["excluded_large_cnv"] > 0]

    g2 = {
        "guard": "copy-number exclusion",
        "question": "is this record gene-specific, or a multi-gene chromosomal event?",
        "naive_emits": naive_total,
        "silently_wrong": excluded,
        "rate": round(excluded / naive_total, 4) if naive_total else None,
        "enforced_emits": kept,
        "genes_reduced_to_zero": zeroed,
        "why_silent": ("a per-gene count is just a number; it looks identical "
                       "whether or not it credits a whole-arm deletion to one gene"),
        "per_gene": [
            {"gene": g["gene"], "naive": g["pathogenic_or_likely"] + g["excluded_large_cnv"],
             "enforced": g["pathogenic_or_likely"], "excluded": g["excluded_large_cnv"]}
            for g in genes
        ],
    }

    # ---- G1: residue verification ------------------------------------
    ab = {a["kind"]: a["records"] for a in fasta.get("abstentions", [])}
    applied = sum(g["applied"] for g in fasta["genes"])
    missense = sum(g["missense"] for g in fasta["genes"])
    truncating = sum(g["nonsense"] for g in fasta["genes"])
    processed = applied + sum(ab.values())
    with_protein_notation = processed - ab.get("no_protein_notation", 0)
    substitution_eligible = with_protein_notation - ab.get("frameshift", 0)
    mismatched = ab.get("residue_mismatch", 0)
    out_of_range = ab.get("position_out_of_range", 0)
    # A naive pipeline completes every eligible substitution except the ones
    # that fail loudly on array bounds.
    naive_emits = substitution_eligible - out_of_range

    g1 = {
        "guard": "residue verification",
        "question": ("does the wild-type residue the record names match the "
                     "canonical sequence at that position?"),
        "records_processed": processed,
        "with_protein_notation": with_protein_notation,
        "substitution_eligible": substitution_eligible,
        "excluded_loud_failures": out_of_range,
        "naive_emits": naive_emits,
        "silently_wrong": mismatched,
        "rate": round(mismatched / naive_emits, 4) if naive_emits else None,
        "enforced_emits": applied,
        "enforced_emits_verified_correct": applied,
        "missense": missense,
        "truncating": truncating,
        "why_silent": ("the FASTA is valid and the residues are real; a folding "
                       "tool accepts it without complaint and returns a "
                       "structure for a protein nobody has"),
    }

    # ---- retention: abstention must be targeted, not blanket ----------
    retention = {
        "note": ("The trivial policy -- refuse everything -- also yields a zero "
                 "silent error rate and is useless. These figures show the "
                 "guards decline specifically what fails a stated check."),
        "sequence_lane": {
            "declined": sum(ab.values()),
            "emitted": applied,
            "emitted_verified_correct": applied,
            "declined_reasons": ab,
        },
        "genetics_lane": {"declined": excluded, "emitted": kept},
    }

    metrics = {
        "schema": "protein_hinge.paper_metrics.v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "corpus": {
            "captured_at": clinvar.get("captured_at"),
            "clinvar_subset_sha256": digest("data/healthomics/clinvar_subset.tsv"),
            "variants_fasta_sha256": digest("data/fasta/variants.fasta"),
            "canonical_fasta_sha256": digest("data/fasta/consensus_genes.fasta"),
            "reconciliation": recon,
        },
        "guards": {"G1_residue_verification": g1, "G2_copy_number_exclusion": g2},
        "retention": retention,
        "not_measured": [
            "whether any proposed drug-disease pairing is biologically correct",
            "generalisation beyond the validation disease",
            "efficacy, treatment value, or clinical utility",
            ("closed-vocabulary resolution (G3) -- reported as a worked example; "
             "n=1 in this corpus, no rate claimed"),
        ],
    }
    OUT_JSON.parent.mkdir(exist_ok=True)
    OUT_JSON.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")

    pct = lambda x: f"{x*100:.1f}%" if x is not None else "n/a"
    md = f"""# Paper metrics — generated, do not edit by hand

Regenerate with `python3 scripts/build_paper_metrics.py`. If the paper
disagrees with this file, the paper is stale.

Corpus captured {metrics['corpus']['captured_at']} ·
subset `sha256:{metrics['corpus']['clinvar_subset_sha256'][:16]}…` ·
variants `sha256:{metrics['corpus']['variants_fasta_sha256'][:16]}…`

Reconciliation: {recon.get('ids_fetched', '?')} records fetched =
{recon.get('kept', '?')} kept + {recon.get('excluded_large_cnv', '?')} excluded +
{recon.get('no_summary_returned', '?')} unavailable
(**{'balanced' if recon.get('balanced') else 'UNBALANCED'}**)

## Silent errors prevented

| Guard | Naive pipeline emits | Silently wrong | Rate | Enforced emits |
|---|---:|---:|---:|---:|
| G1 residue verification | {g1['naive_emits']} | **{g1['silently_wrong']}** | **{pct(g1['rate'])}** | {g1['enforced_emits']} (all verified correct) |
| G2 copy-number exclusion | {g2['naive_emits']} | **{g2['silently_wrong']}** | **{pct(g2['rate'])}** | {g2['enforced_emits']} |

G2 additionally takes **{len(zeroed)} of {len(genes)} genes**
({', '.join(zeroed) if zeroed else 'none'}) from apparent evidence to an honest
zero.

## Cost of enforcement

The sequence lane declines {retention['sequence_lane']['declined']} of
{processed} records and emits {applied}. Declining everything would also score
zero silent errors, so the reasons matter:

| Reason declined | Records |
|---|---:|
""" + "\n".join(f"| {k.replace('_', ' ')} | {v} |" for k, v in
                sorted(ab.items(), key=lambda kv: -kv[1])) + f"""

## Per-gene effect of G2

| Gene | Naive count | Enforced | Excluded |
|---|---:|---:|---:|
""" + "\n".join(f"| {r['gene']} | {r['naive']} | {r['enforced']} | {r['excluded']} |"
                for r in g2["per_gene"]) + """

## Not measured

""" + "\n".join(f"- {x}" for x in metrics["not_measured"]) + "\n"

    OUT_MD.write_text(md, encoding="utf-8")

    print(f"G1 residue verification : {g1['silently_wrong']}/{g1['naive_emits']} = {pct(g1['rate'])}")
    print(f"G2 copy-number exclusion: {g2['silently_wrong']}/{g2['naive_emits']} = {pct(g2['rate'])}")
    print(f"genes reduced to zero   : {len(zeroed)} ({', '.join(zeroed)})")
    print(f"reconciliation balanced : {recon.get('balanced')}")
    print(f"wrote {OUT_JSON.relative_to(ROOT)} and {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
