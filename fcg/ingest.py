#!/usr/bin/env python3
"""
Build the Protein Hinge Fractal Custody Graph from real sources.

Every node in this graph is named by the hash of what it asserts. Every source
was hashed at the point where the bytes originated. Every derived object names
the inputs it consumed. Nothing is admitted unless it recomputes.

Run:  python3 ingest.py
Out:  ./store/nodes/*.json, ./store/merkle_receipt.json, ./store/index.json,
      ./store/routes/*.json
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from fcg import FCG, MERKLE_CONVENTION, verify_receipt  # noqa: E402

STORE = os.path.join(HERE, "store")
ORIGINS = os.path.join(HERE, "origin_digests.json")
STATE_YAML = os.path.abspath(os.path.join(HERE, "..", "..", "HACKDAY_STATE.yaml"))

BUCKET = "https://cellpainting-gallery.s3.amazonaws.com"
DATASET = "cpg0016-jump"

# The eight consensus knockouts, verified against live JUMP metadata.
CONSENSUS = [
    ("TAZ",     "JCP2022_806962", 6901,   "E06", 1, "cardiolipin transacylase; the Barth gene"),
    ("CRLS1",   "JCP2022_801511", 54675,  "M04", 1, "cardiolipin synthase; terminal CL synthesis"),
    ("PGS1",    "JCP2022_805090", 9489,   "J03", 1, "PGP synthase; committed step into CL"),
    ("PTPMT1",  "JCP2022_805673", 114971, "H14", 1, "PGP phosphatase; CL pathway"),
    ("HADHA",   "JCP2022_803009", 3030,   "D13", 2, "monolysocardiolipin acyltransferase activity"),
    ("PHB",     "JCP2022_805091", 5245,   "G22", 2, "prohibitin scaffold; CL-binding"),
    ("PHB2",    "JCP2022_805092", 11331,  "E17", 2, "prohibitin scaffold; CL-binding"),
    ("CHCHD3",  "JCP2022_801279", 54927,  "G04", 2, "MICOS; cristae junction architecture"),
]

CONTROLS = [
    ("JCP2022_800001", "no-guide",       "CRISPR negative control"),
    ("JCP2022_800002", "non-targeting",  "CRISPR negative control, 10 wells/plate"),
    ("JCP2022_805264", "PLK1",           "CRISPR positive control"),
    ("JCP2022_033924", "DMSO",           "compound vehicle control"),
]


def plate_uri(source, batch, plate):
    return f"{BUCKET}/{DATASET}/{source}/workspace/profiles/{batch}/{plate}/{plate}.parquet"


def main():
    with open(ORIGINS) as fh:
        origins = json.load(fh)
    groups = {g["group"]: g for g in origins["groups"]}

    # The clock is pinned to the observation date, not to wall time. Node ids
    # hash node bodies, so a live clock would rename the whole graph on every
    # run. Pinned, the graph is byte-reproducible: run it twice, same root.
    g = FCG(STORE, clock=origins["captured_on"] + "T00:00:00Z")

    # ---------------------------------------------------------------- layer 0
    # SOURCES. Two honest kinds, never conflated.
    #   attested = hashed at origin, bytes not held  -> COMMITTED
    #   local    = bytes held in the atom store      -> RECOMPUTED

    meta_nodes = {}
    mg = groups["jump_metadata"]
    for it in mg["items"]:
        uri = mg["uri_template"].format(file=it["file"])
        meta_nodes[it["file"]] = g.add_source_attested(
            label=f"jump_metadata/{it['file']}",
            uri=uri, digest=it["sha256"], nbytes=it["bytes"],
            extra={"origin_repo": mg["origin_repo"], "ref": mg["ref"],
                   "http_status": it["http_status"]},
        )

    crispr_plates, target2_plates = {}, {}
    pg = groups["jump_profiles"]
    for it in pg["items"]:
        uri = plate_uri(pg["source"], it["batch"], it["plate"])
        nid = g.add_source_attested(
            label=f"profiles/{it['plate']}",
            uri=uri, digest=it["sha256"], nbytes=it["bytes"],
            extra={"dataset": DATASET, "source": pg["source"], "batch": it["batch"],
                   "plate": it["plate"], "plate_type": it["plate_type"],
                   "http_status": it["http_status"]},
        )
        (crispr_plates if it["plate_type"] == "CRISPR" else target2_plates)[it["plate"]] = nid

    partner_nodes = {}
    bg = groups["partner_run_biobitworks"]
    for it in bg["items"]:
        uri = bg["uri_template"].format(file=it["file"])
        partner_nodes[it["file"]] = g.add_source_attested(
            label="partner/" + it["file"].split("/")[-1],
            uri=uri, digest=it["sha256"], nbytes=it["bytes"],
            extra={"origin_repo": bg["origin_repo"], "ref": bg["ref"],
                   "party": "biobitworks", "adopted": False,
                   "custody_note": bg["custody_note"],
                   "http_status": it["http_status"]},
        )

    contract = g.add_source_local(
        label="HACKDAY_STATE.yaml",
        path=STATE_YAML,
        origin="authored locally; the binding execution contract for this run",
    )

    # ---------------------------------------------------------------- layer 1
    # The design decisions, each pinned to the sources that justify it.

    axis_spec = g.add_derivation(
        label="consensus_axis_specification", layer=1,
        fn="specify_consensus_knockout_axis",
        inputs=[contract, meta_nodes["crispr.csv.gz"], meta_nodes["well.csv.gz"],
                meta_nodes["plate.csv.gz"]],
        payload={
            "definition": ("The disease direction is the consensus of several independent "
                           "knockouts of the cardiolipin/cristae module, not any single gene. "
                           "A direction reproduced by unrelated genes is a pathway signal; a "
                           "direction from one gene is that gene's idiosyncrasy."),
            "genes": [
                {"gene": n, "jcp": j, "entrez": e, "well": w, "tier": t, "why": why}
                for n, j, e, w, t, why in CONSENSUS
            ],
            "tier_1_required": [n for n, _, _, _, t, _ in CONSENSUS if t == 1],
            "tier_2_optional": [n for n, _, _, _, t, _ in CONSENSUS if t == 2],
            "controls": [{"jcp": j, "name": n, "role": r} for j, n, r in CONTROLS],
            "excluded": {
                "TAZ_ORF_JCP2022_910418": ("cross-source (source_4, batch 2021_05_10_Batch3). "
                                           "Mixing sources introduces batch structure we cannot "
                                           "separate from biology in one day. Tier 3, not used."),
                "SS-31": ("elamipretide is a peptide and is not in the JUMP compound library. "
                          "It is the motivation for this project and is never a comparator."),
            },
        },
        params={"tier_1_min_genes": 3, "replicates_per_gene": 7},
    )

    reference_frame = g.add_derivation(
        label="within_plate_reference_frame", layer=1,
        fn="declare_normalization_frame",
        inputs=[axis_spec] + sorted(crispr_plates.values()),
        payload={
            "frame": "per-plate robust z-score against that plate's negative controls",
            "reason": ("CRISPR and TARGET2 plates come from the same site and the same runs "
                       "(source_13), so plate is the only batch variable that must be removed. "
                       "Normalizing within plate makes the two arms comparable without "
                       "cross-site harmonization."),
            "crispr_plates": sorted(crispr_plates),
            "negative_controls": ["JCP2022_800001", "JCP2022_800002"],
            "positive_control": "JCP2022_805264",
        },
    )

    compound_frame = g.add_derivation(
        label="compound_arm_frame", layer=1,
        fn="declare_compound_arm",
        inputs=[axis_spec, meta_nodes["compound.csv.gz"],
                meta_nodes["perturbation_control.csv"]] + sorted(target2_plates.values()),
        payload={
            "library": "TARGET2",
            "perturbations": 302,
            "wells": 2304,
            "plates": sorted(target2_plates),
            "vehicle": "JCP2022_033924 (DMSO)",
            "batch_alignment": ("same source_13 batches as the CRISPR arm; "
                                "20220914_Run1 / 20221009_Run2 / 20221017_Run3 / "
                                "20221109_Run5 / 20221120_Run6"),
        },
    )

    # ---------------------------------------------------------------- layer 2
    ranking_method = g.add_derivation(
        label="counter_perturbation_ranking_method", layer=2,
        fn="rank_by_cosine_against_consensus_axis",
        inputs=[axis_spec, reference_frame, compound_frame],
        payload={
            "step_1": "Build the consensus disease axis from tier-1 knockout profiles.",
            "step_2": "Project every TARGET2 compound profile onto that axis.",
            "step_3": "Score = cosine similarity to the axis. Most negative ranks first.",
            "step_4": "A negative score means the compound moves cells opposite to the "
                      "direction the knockouts move them.",
            "step_5": "Report the null: shuffle labels, recompute, disclose enrichment.",
            "what_this_is_not": ("This never compares anything to SS-31. It compares compounds "
                                 "to the genetic lesion. A hit is a compound whose morphology "
                                 "opposes the lesion's morphology. That is a hypothesis about "
                                 "direction, not a measurement of rescue."),
        },
        params={"metric": "cosine", "sort": "ascending", "null_model": "label_shuffle",
                "shuffle_iterations": 1000},
    )

    partner_crosscheck = g.add_derivation(
        label="partner_receipt_crosscheck", layer=2,
        fn="verify_third_party_merkle_receipt",
        inputs=[partner_nodes["data/magicstudiobox/runs/primary/merkle_receipt.json"],
                partner_nodes["data/magicstudiobox/runs/primary/tamper_test.json"],
                partner_nodes["data/magicstudiobox/runs/primary/evaluation.json"]],
        payload={
            "finding": ("The partner receipt lists six digests and one root but does not declare "
                        "the tree convention used to combine them. We tested the standard "
                        "families (RFC 6962, duplicate-last, carry-odd, sorted-pair, raw and hex "
                        "concatenation) and did not reproduce the stated root."),
            "verdict": "COMMITTED",
            "why_not_recomputed": ("A root that cannot be independently recomputed is asserted, "
                                   "not proven. We pin the file by digest so the assertion is "
                                   "fixed in place, and we stop there."),
            "this_is_not_an_accusation": ("Nothing here suggests the partner root is wrong. It "
                                          "says the receipt is missing one field, and that the "
                                          "missing field is the difference between COMMITTED and "
                                          "RECOMPUTED."),
            "fix": "Add \"merkle_convention\", \"leaf_hash\", \"node_hash\", \"leaf_order\".",
            "our_declaration": MERKLE_CONVENTION,
            "partner_disclosed_negative": {
                "known_pair_rank": 28, "reciprocal_rank": 0.0357,
                "hits_at_1_5_10": False,
                "note": "The partner disclosed a miss rather than hiding it. That is the "
                        "behaviour this ledger is built to reward.",
            },
        },
    )

    # ---------------------------------------------------------------- layer 3
    claim = g.add_claim(
        label="phase_1_axis_claim",
        statement=(
            "A consensus counter-perturbation axis for the cardiolipin/cristae module is "
            "constructible from JUMP cpg0016 source_13 alone, and the TARGET2 compound arm "
            "shares the same plates and batches, so compounds can be ranked against the "
            "genetic lesion without cross-site harmonization."
        ),
        level="COMMITTED",
        inputs=[ranking_method, partner_crosscheck, contract],
        evidence={
            "sources_pinned": len(mg["items"]) + len(pg["items"]) + len(bg["items"]) + 1,
            "crispr_plates": len(crispr_plates),
            "target2_plates": len(target2_plates),
            "consensus_genes": len(CONSENSUS),
            "all_origins_http_200": True,
            "what_is_established": "Feasibility and provenance. The data exists, is reachable, "
                                   "and is pinned by digest.",
            "what_is_not_established": "No compound has been scored. No axis has been computed. "
                                       "No rescue has been measured in any cell.",
        },
        claim_ceiling="REPURPOSING_HYPOTHESIS",
    )

    written = g.flush()

    # ------------------------------------------------------------- report
    receipt = g.receipt()
    v = verify_receipt(receipt)
    verdict = g.admit(claim)

    print("=" * 74)
    print("BIOCUSTODY FRACTAL CUSTODY GRAPH")
    print("=" * 74)
    print(f"nodes            {len(g.nodes)}")
    def _k(n):
        return n["kind"] if isinstance(n, dict) else n.kind

    def _held(n):
        c = n["custody"] if isinstance(n, dict) else n.custody
        return bool(c.get("bytes_held"))

    vals = list(g.nodes.values())
    src = [n for n in vals if _k(n) == "SOURCE"]
    print(f"  layer 0 source {len(src)}"
          f"  (attested {sum(1 for n in src if not _held(n))}"
          f", held {sum(1 for n in src if _held(n))})")
    print(f"  derivation     {sum(1 for n in vals if _k(n) == 'DERIVATION')}")
    print(f"  claim          {sum(1 for n in vals if _k(n) == 'CLAIM')}")
    print(f"convention       {receipt['merkle_convention']}")
    print(f"leaf_order       {receipt['leaf_order']}")
    print(f"MERKLE ROOT      {receipt['merkle_root']}")
    print(f"receipt verified {v['verified']}  level={v['level']}")
    print(f"claim admission  {'ADMITTED' if verdict['admitted'] else 'REJECTED'}"
          f"  ({verdict.get('evidence_level') or verdict.get('reason')})")
    print()

    route = g.route(claim)
    print("-" * 74)
    print("MERKLE ROUTE  (the spin-out proof: hand this to a stranger)")
    print("-" * 74)
    print(f"leaf_index       {route['leaf_index']} of {receipt['leaf_count']}")
    print(f"leaf_hash        {route['leaf_hash']}")
    for i, step in enumerate(route["path"]):
        print(f"  step {i}  {step['side']:>5}  {step['sibling']}")
    print(f"replays to root  {route['merkle_root']}")
    print(f"route_verified   {route['route_verified']}")
    print()

    print("-" * 74)
    print("CHAIN OF CUSTODY  (claim -> point of origin)")
    print("-" * 74)
    for row in route["custody_chain"]:
        held = "held" if row.get("bytes_held") else "attested"
        origin = row.get("origin") or "(derived; holds no external origin)"
        if len(origin) > 46:
            origin = "..." + origin[-43:]
        print(f"  L{row['layer']} {row['kind']:<10} {row['label'][:34]:<34} {held:<8} {origin}")
    print()
    # Persist the route as a standalone, self-verifying object. This is the
    # thing that leaves the building when an artifact spins out.
    route_path = os.path.join(STORE, "routes", claim.split(":", 1)[1][:16] + ".json")
    with open(route_path, "w") as fh:
        json.dump(route, fh, indent=2, sort_keys=True)

    print(f"nodes written    {written['leaf_count']} -> {os.path.join(STORE, 'nodes')}")
    print(f"receipt          {os.path.join(STORE, 'merkle_receipt.json')}")
    print(f"route            {route_path}")
    return g, claim


if __name__ == "__main__":
    main()
