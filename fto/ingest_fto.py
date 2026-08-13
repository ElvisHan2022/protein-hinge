#!/usr/bin/env python3
"""
Build the FTO lane on top of the science graph.

The science graph (fcg/ingest.py) is built first and unchanged. This module
attaches the FTO lane to it, so a single Merkle root covers both. That is the
point: the provenance of "who else is working on this" is held to the same
standard as the provenance of a parquet file.

Run:  python3 ingest_fto.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "fcg"))

import ingest as science  # noqa: E402
from fcg import verify_receipt  # noqa: E402
from fto import (FTO_CEILING, REGISTRIES, add_search, add_triage,  # noqa: E402
                 emit_finding, registry_status)

REGDIG = os.path.join(HERE, "registry_digests.json")
STORE = os.path.join(HERE, "..", "fcg", "store")

# SCREENED requires a named human. This is that name. Change it if someone else
# does the reading; do not leave it pointing at a person who did not.
REVIEWER = "Yassa (yassine@ucsb.edu)"


def main():
    with open(REGDIG) as fh:
        rd = json.load(fh)
    corpus_date = rd["captured_on"]

    # Build the science graph, quietly.
    devnull = open(os.devnull, "w")
    real, sys.stdout = sys.stdout, devnull
    g, science_claim = science.main()
    sys.stdout = real

    root_science_only = g.receipt()["merkle_root"]
    by_reg = {r["registry"]: r for r in rd["registries"]}

    # ------------------------------------------------------------ layer 0
    # Every query response, hashed at origin. We hold digests, not rights.
    src = {}
    for key in ("clinicaltrials_gov", "openfda_drug", "open_targets"):
        reg = by_reg[key]
        for q in reg["queries"]:
            label = q.get("label") or f"opentargets_{q['gene']}"
            uri = reg["endpoint"]
            src[label] = g.add_source_attested(
                label=f"fto/{key}/{label}",
                uri=uri, digest=q["sha256"], nbytes=q["bytes"],
                extra={
                    "registry": key,
                    "registry_name": REGISTRIES[key]["name"],
                    "lane": reg["lane"],
                    "corpus_date": corpus_date,
                    "query": q.get("params") or {"ensemblId": q.get("ensembl")},
                    "result_count": q.get("result_count"),
                    "http_status": q["http_status"],
                    "not_date_pinned": True,
                    "reverify_caveat": ("This endpoint serves live data. Re-fetching "
                                        "on a later date will return different bytes "
                                        "and a different digest. That is a corpus "
                                        "change, not a tamper."),
                },
            )

    # ------------------------------------------------------------ layer 1
    ct = by_reg["clinicaltrials_gov"]
    s_ct = add_search(
        g, "fto_search_competitive_landscape", "clinicaltrials_gov",
        query=[q["params"] for q in ct["queries"]],
        corpus_date=corpus_date,
        result_source_ids=[src[q["label"]] for q in ct["queries"]],
        result_count=sum(q["result_count"] for q in ct["queries"]),
        lane="C",
    )

    fda = by_reg["openfda_drug"]
    s_fda = add_search(
        g, "fto_search_incumbent_label", "openfda_drug",
        query=[q["params"] for q in fda["queries"]],
        corpus_date=corpus_date,
        result_source_ids=[src[q["label"]] for q in fda["queries"]],
        result_count=sum(q["result_count"] for q in fda["queries"]),
        lane="C",
    )

    ot = by_reg["open_targets"]
    s_ot = add_search(
        g, "fto_search_target_tractability", "open_targets",
        query={"graphql": ot["graphql_query"],
               "targets": [q["ensembl"] for q in ot["queries"]]},
        corpus_date=corpus_date,
        result_source_ids=[src[f"opentargets_{q['gene']}"] for q in ot["queries"]],
        result_count=len(ot["queries"]),
        lane="C",
    )

    # ------------------------------------------------------------ layer 2
    t_ct = add_triage(
        g, "fto_triage_competitive_landscape", [s_ct],
        reviewer=REVIEWER, reviewed_at=corpus_date,
        blocking=[],
        adjacent=[
            {"nct": s["nct"], "sponsor": "Stealth BioTherapeutics Inc.",
             "phase": s.get("phase"), "status": s["status"],
             "why_adjacent": "Same indication, different modality (peptide). "
                             "Defines the incumbent, not a bar to a small molecule."}
            for s in ct["extracted"]["stealth_studies"]
        ],
        irrelevant_count=len(ct["extracted"]["non_drug_or_unrelated"]),
        rationale=(ct["extracted"]["finding"] + " " + ct["extracted"]["caveat"]),
    )

    t_ot = add_triage(
        g, "fto_triage_target_tractability", [s_ot],
        reviewer=REVIEWER, reviewed_at=corpus_date,
        blocking=[],
        adjacent=[{
            "observation": "0/8 consensus genes have any small-molecule "
                           "tractability bucket; 0 have drug or clinical candidates",
            "positive_control": ot["positive_control"],
            "why_adjacent": ot["extracted"]["why_this_supports_the_design"],
            "counterweight": ot["extracted"]["why_this_is_also_the_main_caveat"],
        }],
        irrelevant_count=0,
        rationale=ot["extracted"]["finding"],
    )

    # ------------------------------------------------------------ layer 3
    f_data = emit_finding(
        g, "fto_finding_lane_D_data", "D",
        statement=("Every input consumed by this project is Cell Painting Gallery "
                   "data under CC0 1.0 Universal, a public-domain dedication with "
                   "no field-of-use, non-commercial, or share-alike restriction. "
                   "Lane D is clear. Lane D clearing carries no implication for "
                   "lanes M or C."),
        level="SCREENED",
        inputs=[science_claim],
        evidence={
            "license": "CC0 1.0 Universal",
            "citation_is_ethical_not_legal": True,
            "cite": ["JUMP Cell Painting dataset paper",
                     "Weisbart et al. 2024, Cell Painting Gallery"],
            "trapdoor": ("CC0 on a morphological profile says nothing about rights "
                         "in the molecule the profile depicts. Lane C is separate "
                         "and open."),
            "partner_artifacts": ("biobitworks/aws-biopharma content is pinned by "
                                  "digest and marked adopted:false. Pinning records "
                                  "what was served. It does not license it."),
        },
    )

    f_comp = emit_finding(
        g, "fto_finding_lane_C_competitive", "C",
        statement=("The registered interventional drug field in Barth syndrome is "
                   "effectively one company. Absence of a registered competitor is "
                   "weak evidence of no competitor, because ClinicalTrials.gov "
                   "registers trials rather than programs."),
        level="SCREENED",
        inputs=[t_ct, s_fda],
        evidence={
            "barth_studies": ct["extracted"]["barth_syndrome_studies"],
            "interventional_drug_sponsors": ct["extracted"]["interventional_drug_sponsors"],
            "stealth_studies": ct["extracted"]["stealth_studies"],
            "incumbent_label_present_in_openfda": True,
            "not_searched_yet": ["method-of-treatment patent claims naming Barth "
                                 "syndrome or cardiolipin",
                                 "FDA orphan designation database (no stable API)"],
            "caveat": ct["extracted"]["caveat"],
        },
    )

    f_tract = emit_finding(
        g, "fto_finding_lane_C_tractability", "C",
        statement=("All eight consensus genes score zero on every small-molecule "
                   "tractability bucket and carry zero drug or clinical candidates "
                   "in Open Targets, verified against EGFR as a positive control. "
                   "The cardiolipin/cristae module is undrugged and not obviously "
                   "druggable by structural criteria. This is simultaneously the "
                   "strongest argument for a phenotype-first method and the "
                   "strongest caveat on any hit it produces."),
        level="SCREENED",
        inputs=[t_ot],
        evidence={
            "genes_queried": len(ot["queries"]),
            "genes_with_sm_tractability": 0,
            "genes_with_drug_candidates": 0,
            "positive_control": ot["positive_control"],
            "supports_design": ot["extracted"]["why_this_supports_the_design"],
            "main_caveat": ot["extracted"]["why_this_is_also_the_main_caveat"],
            "orthogonality": ot["extracted"]["orthogonality"],
            "consequence": ("There is no reference chemistry against this module, "
                            "so there is no positive-control compound to validate "
                            "the axis and no prior art to sanity-check a hit "
                            "against. Any ranking will be mechanistically "
                            "unexplained."),
        },
    )

    written = g.flush()
    receipt = g.receipt()
    v = verify_receipt(receipt)

    route = g.route(f_tract)
    route_path = os.path.join(STORE, "routes", f_tract.split(":", 1)[1][:16] + ".json")
    with open(route_path, "w") as fh:
        json.dump(route, fh, indent=2, sort_keys=True)

    # ----------------------------------------------------------- report
    print("=" * 74)
    print("FTO LANE  (attached to the science graph, one root over both)")
    print("=" * 74)
    for r in registry_status():
        mark = "wired" if r["wired"] else "NOT WIRED"
        print(f"  [{r['lane']}] {r['name']:<44} {mark}")
    print()
    print(f"root, science only     {root_science_only}")
    print(f"root, science + FTO    {receipt['merkle_root']}")
    print(f"total nodes            {receipt['leaf_count']}  (+{receipt['leaf_count'] - 41} from FTO)")
    print(f"receipt verified       {v['verified']}  level={v['level']}")
    print(f"FTO ceiling            {FTO_CEILING}")
    print()

    print("-" * 74)
    print("FINDINGS")
    print("-" * 74)
    for nid in (f_data, f_comp, f_tract):
        n = g.nodes[nid]
        a = g.admit(nid)
        print(f"  {n.label}")
        print(f"    admitted {a['admitted']}  ceiling {n.claim['claim_ceiling']}")
    print()

    print("-" * 74)
    print(f"MERKLE ROUTE for {g.nodes[f_tract].label}")
    print("-" * 74)
    print(f"leaf_index      {route['leaf_index']} of {receipt['leaf_count']}")
    print(f"leaf_hash       {route['leaf_hash']}")
    for i, step in enumerate(route["path"]):
        print(f"  step {i}  {step['side']:>5}  {step['sibling']}")
    print(f"replays to root {route['merkle_root']}")
    print(f"route_verified  {route['route_verified']}")
    print()
    print(f"route written   {route_path}")

    print()
    print("-" * 74)
    print("REFUSAL CHECK")
    print("-" * 74)
    try:
        emit_finding(g, "x", "C", "we are clear to operate", "FTO_OPINION", [], {})
        print("  FAIL: FTO_OPINION was emitted")
    except ValueError as e:
        print(f"  PASS: refused FTO_OPINION -- {str(e).splitlines()[0]}")
    return g


if __name__ == "__main__":
    main()
