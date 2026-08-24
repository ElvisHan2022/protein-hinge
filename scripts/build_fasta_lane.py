#!/usr/bin/env python3
"""Build the FASTA lane: canonical sequences + ClinVar variant-substituted sequences.

No AWS required. Resolves each consensus gene to its reviewed human UniProt
entry, pulls the canonical sequence, then reconstructs protein sequences for
the pathogenic variants already held in data/healthomics/clinvar_subset.tsv.

Outputs
  data/fasta/consensus_genes.fasta   wild-type canonical sequences (8 genes)
  data/fasta/variants.fasta          variant-substituted sequences
  data/fasta/fasta_provenance.json   query URLs, response digests, abstentions
  site/assets/fasta_lane.json        dashboard projection

House rules honoured here:
  * every UniProt response is hashed at capture; the query URL is recorded
  * a substitution is applied ONLY if the wild-type residue named by ClinVar
    matches the canonical sequence at that position. A mismatch means the
    record is numbered against a different isoform/transcript, so the row
    ABSTAINS rather than emitting a plausible-but-wrong sequence
  * frameshift / indel / unparseable notation abstains with a named reason

Claim ceiling: SEQUENCE_RECORD. These are folding and assay *inputs* derived
from public records. Nothing here is a structure, a binding claim, or a
prediction of pathogenicity.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLINVAR_TSV = ROOT / "data" / "healthomics" / "clinvar_subset.tsv"
OUT_DIR = ROOT / "data" / "fasta"
SITE_ASSETS = ROOT / "site" / "assets"

UNIPROT = "https://rest.uniprot.org/uniprotkb/search"

# The eight consensus knockouts (fcg/ingest.py). ClinVar's gene column uses
# TAFAZZIN; UniProt indexes prohibitin under PHB1 since the HGNC rename.
GENES = ["TAFAZZIN", "CRLS1", "PGS1", "PTPMT1", "HADHA", "PHB", "PHB2", "CHCHD3"]
GENE_ALIASES = {"PHB": ["PHB", "PHB1"], "TAFAZZIN": ["TAFAZZIN", "TAZ"]}

AA3 = {
    "Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C", "Gln": "Q",
    "Glu": "E", "Gly": "G", "His": "H", "Ile": "I", "Leu": "L", "Lys": "K",
    "Met": "M", "Phe": "F", "Pro": "P", "Ser": "S", "Thr": "T", "Trp": "W",
    "Tyr": "Y", "Val": "V", "Sec": "U", "Pyl": "O",
}

# p.Leu266Pro | p.Arg57Ter | p.Thr43fs | p.(Leu266Pro)
HGVS_P = re.compile(r"p\.\(?([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2}|Ter|\*|fs)\)?")


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "protein-hinge-demo/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def resolve_gene(gene: str, provenance: list) -> dict | None:
    """Reviewed human UniProt entry for a gene symbol, with its receipt."""
    for symbol in GENE_ALIASES.get(gene, [gene]):
        url = UNIPROT + "?" + urllib.parse.urlencode({
            "query": f"gene_exact:{symbol} AND organism_id:9606 AND reviewed:true",
            "fields": "accession,id,protein_name,sequence",
            "format": "json",
            "size": "1",
        })
        raw = fetch(url)
        provenance.append({
            "gene": gene, "queried_symbol": symbol, "url": url,
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
        })
        results = json.loads(raw).get("results", [])
        if results:
            r = results[0]
            return {
                "gene": gene,
                "accession": r.get("primaryAccession", ""),
                "entry": r.get("uniProtkbId", ""),
                "protein": (r.get("proteinDescription", {})
                             .get("recommendedName", {})
                             .get("fullName", {})
                             .get("value", "")),
                "sequence": r.get("sequence", {}).get("value", ""),
                "length": r.get("sequence", {}).get("length", 0),
            }
        time.sleep(0.2)
    return None


def read_clinvar_rows() -> list:
    rows = []
    with CLINVAR_TSV.open(encoding="utf-8") as f:
        cols = f.readline().rstrip("\n").split("\t")
        for line in f:
            vals = line.rstrip("\n").split("\t")
            if len(vals) == len(cols):
                rows.append(dict(zip(cols, vals)))
    return rows


def apply_variant(seq: str, title: str):
    """Return (variant_sequence, info). variant_sequence is None on abstention."""
    m = HGVS_P.search(title or "")
    if not m:
        return None, {"kind": "no_protein_notation",
                      "reason": "record carries no p. (protein-level) change"}
    wt3, pos_s, alt = m.group(1), m.group(2), m.group(3)
    pos = int(pos_s)
    hgvs_p = f"p.{wt3}{pos}{alt}"
    wt = AA3.get(wt3)
    if wt is None:
        return None, {"kind": "unknown_residue", "hgvs_p": hgvs_p,
                      "reason": f"unrecognised residue code {wt3}"}
    if pos < 1 or pos > len(seq):
        return None, {"kind": "position_out_of_range", "hgvs_p": hgvs_p,
                      "reason": f"position {pos} exceeds canonical length {len(seq)}"}
    if seq[pos - 1] != wt:
        return None, {"kind": "residue_mismatch", "hgvs_p": hgvs_p,
                      "reason": (f"canonical residue at {pos} is {seq[pos-1]}, "
                                 f"ClinVar names {wt} - different isoform numbering")}
    if alt == "fs":
        return None, {"kind": "frameshift", "hgvs_p": hgvs_p,
                      "reason": "downstream sequence not reconstructable from ClinVar title"}
    if alt in ("Ter", "*"):
        truncated = seq[:pos - 1]
        if not truncated:
            return None, {"kind": "empty_product", "hgvs_p": hgvs_p,
                          "reason": "truncation at position 1 leaves no product"}
        return truncated, {"kind": "nonsense", "hgvs_p": hgvs_p,
                           "note": f"truncated at {pos}; {len(truncated)} aa retained"}
    alt1 = AA3.get(alt)
    if alt1 is None:
        return None, {"kind": "unknown_residue", "hgvs_p": hgvs_p,
                      "reason": f"unrecognised substituted residue {alt}"}
    return seq[:pos - 1] + alt1 + seq[pos:], {
        "kind": "missense", "hgvs_p": hgvs_p,
        "note": f"{wt}{pos}{alt1} applied to canonical sequence"}


def wrap(seq: str, width: int = 60) -> str:
    return "\n".join(seq[i:i + width] for i in range(0, len(seq), width))


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SITE_ASSETS.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    provenance = {
        "schema": "protein_hinge.fasta_lane.v1",
        "captured_at": now,
        "claim_ceiling": "SEQUENCE_RECORD",
        "source": "UniProtKB reviewed human entries + ClinVar subset held locally",
        "clinvar_input": {
            "path": "data/healthomics/clinvar_subset.tsv",
            "sha256": hashlib.sha256(CLINVAR_TSV.read_bytes()).hexdigest(),
        },
        "uniprot_queries": [],
        "genes": [],
        "abstentions": [],
    }

    canon = {}
    for gene in GENES:
        rec = resolve_gene(gene, provenance["uniprot_queries"])
        if rec is None or not rec["sequence"]:
            provenance["abstentions"].append({
                "stage": "uniprot", "gene": gene,
                "reason": "no reviewed human entry returned",
            })
            continue
        canon[gene] = rec
        time.sleep(0.2)

    # ---- wild-type FASTA ------------------------------------------------
    wt_lines = []
    for gene in GENES:
        rec = canon.get(gene)
        if not rec:
            continue
        wt_lines.append(
            f">sp|{rec['accession']}|{rec['entry']} {rec['protein']} "
            f"GN={gene} len={rec['length']} claim=SEQUENCE_RECORD\n{wrap(rec['sequence'])}")
    wt_path = OUT_DIR / "consensus_genes.fasta"
    wt_path.write_text("\n".join(wt_lines) + "\n", encoding="ascii", newline="\n")

    # ---- variant FASTA --------------------------------------------------
    rows = read_clinvar_rows()
    var_lines = []
    per_gene = {g: {"applied": 0, "missense": 0, "nonsense": 0, "abstained": 0}
                for g in GENES}
    abstain_kinds = {}
    examples = []

    for row in rows:
        gene = row.get("gene", "")
        rec = canon.get(gene)
        if not rec:
            continue
        seq, info = apply_variant(rec["sequence"], row.get("title", ""))
        if seq is None:
            per_gene[gene]["abstained"] += 1
            kind = info["kind"]
            abstain_kinds[kind] = abstain_kinds.get(kind, 0) + 1
            continue
        per_gene[gene]["applied"] += 1
        per_gene[gene][info["kind"]] += 1
        header = (f">{gene}|{rec['accession']}|{row.get('accession','')}"
                  f"|{info['hgvs_p']}|{info['kind']}|len={len(seq)}"
                  f"|claim=SEQUENCE_RECORD")
        var_lines.append(f"{header}\n{wrap(seq)}")
        if len(examples) < 8 and info["kind"] == "missense":
            examples.append({"gene": gene, "accession": row.get("accession", ""),
                             "hgvs_p": info["hgvs_p"], "note": info["note"],
                             "length": len(seq)})

    var_path = OUT_DIR / "variants.fasta"
    var_path.write_text(("\n".join(var_lines) + "\n") if var_lines else "",
                        encoding="ascii", newline="\n")

    for kind, n in sorted(abstain_kinds.items(), key=lambda kv: -kv[1]):
        provenance["abstentions"].append({"stage": "variant_reconstruction",
                                          "kind": kind, "records": n})
    for gene in GENES:
        rec = canon.get(gene)
        provenance["genes"].append({
            "gene": gene,
            "accession": rec["accession"] if rec else None,
            "canonical_length": rec["length"] if rec else None,
            **per_gene[gene],
        })

    wt_digest = hashlib.sha256(wt_path.read_bytes()).hexdigest()
    var_digest = hashlib.sha256(var_path.read_bytes()).hexdigest()
    provenance["outputs"] = {
        "consensus_genes.fasta": {"sha256": wt_digest, "records": len(wt_lines)},
        "variants.fasta": {"sha256": var_digest, "records": len(var_lines)},
    }
    (OUT_DIR / "fasta_provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lane = {
        "schema": "protein_hinge.fasta_lane.projection.v1",
        "captured_at": now,
        "claim_ceiling": "SEQUENCE_RECORD",
        "note": ("Canonical sequences from UniProt, plus protein sequences "
                 "reconstructed from the pathogenic ClinVar records this project "
                 "already holds. A substitution is applied only when the "
                 "wild-type residue matches the canonical sequence at that "
                 "position; everything else abstains with a named reason. These "
                 "are folding and assay inputs - not structures, not binding "
                 "claims, not predictions of pathogenicity."),
        "wt_fasta": {"path": "data/fasta/consensus_genes.fasta",
                     "sha256": wt_digest, "records": len(wt_lines)},
        "variant_fasta": {"path": "data/fasta/variants.fasta",
                          "sha256": var_digest, "records": len(var_lines)},
        "genes": provenance["genes"],
        "abstentions": [a for a in provenance["abstentions"]
                        if a["stage"] == "variant_reconstruction"],
        "examples": examples,
    }
    (SITE_ASSETS / "fasta_lane.json").write_text(
        json.dumps(lane, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"canonical sequences : {len(wt_lines)} / {len(GENES)} genes")
    print(f"variant sequences   : {len(var_lines)} written")
    kinds = ", ".join(f"{k}={v}" for k, v in
                      sorted(abstain_kinds.items(), key=lambda kv: -kv[1]))
    print(f"abstained           : {kinds if kinds else 'none'}")
    print(f"wt   sha256 {wt_digest[:16]}...  {wt_path.relative_to(ROOT)}")
    print(f"var  sha256 {var_digest[:16]}...  {var_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
