#!/usr/bin/env python3
"""
Tamper test. A custody ledger that never rejects anything is decoration.

There are exactly two ways to alter this graph, and the test runs both.

  ARM A -- change the stored bytes, leave the record alone.
    The recorded digest no longer matches the bytes. Admission fails.
    The Merkle root does NOT move, and that is correct: the root is a
    commitment to what was CLAIMED, not a checksum of the disk. Detection
    here comes from recomputation, not from the root.

  ARM B -- change the bytes AND repair the record to match. The cover-up.
    Recomputation now passes. But the node id is the hash of the record,
    so repairing the record renames the node, and renaming the node moves
    the root. Detection here comes from the root, not from recomputation.

The point is the conjunction: there is no edit that survives both checks.
Arm A trips recomputation. Arm B trips the root. An attacker must pick one.

Then it restores everything and demands the graph re-admits cleanly and the
root returns to its original value.

Run:  python3 tamper_test.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from fcg import SCHEMA_TAMPER, canonical  # noqa: E402
from ingest import main as build  # noqa: E402

OUT = os.path.join(HERE, "store", "tamper_test.json")


def banner(t):
    print()
    print("=" * 74)
    print(t)
    print("=" * 74)


def main():
    # quiet the ingest report
    devnull = open(os.devnull, "w")
    real = sys.stdout
    sys.stdout = devnull
    g, claim = build()
    sys.stdout = real

    root_before = g.receipt()["merkle_root"]
    before = g.admit(claim)

    # Pick a real upstream target: the layer-1 axis specification. It is three
    # hops below the claim, and the claim never mentions it directly.
    target = next(nid for nid, n in g.nodes.items()
                  if n.label == "consensus_axis_specification")
    atom = os.path.join(g.root, "atoms", g.nodes[target].content_digest.split(":", 1)[1])

    with open(atom, "rb") as fh:
        original = fh.read()

    # The edit is deliberately trivial and semantically meaningful: move TAZ
    # from well E06 to E07. One character. Nothing about the file looks wrong,
    # and every downstream number would be computed from the wrong wells.
    assert original.count(b'"well":"E06"') == 1
    tampered = original.replace(b'"well":"E06"', b'"well":"E07"')
    assert tampered != original, "tamper target not found in atom bytes"

    banner("TAMPER TEST -- ARM A: alter the bytes, leave the record")
    print(f"target node     {g.nodes[target].label}")
    print(f"target node_id  {target}")
    print(f"edit            TAZ well E06 -> E07  (one character)")
    print(f"bytes before    {len(original)}   after {len(tampered)}")
    print()
    print(f"BEFORE  claim admitted        {before['admitted']}  ({before.get('evidence_level')})")
    print(f"BEFORE  merkle_root           {root_before}")

    with open(atom, "wb") as fh:
        fh.write(tampered)
    try:
        after_target = g.admit(target)
        after_claim = g.admit(claim)
        route_after = g.route(claim)
        root_after = g.receipt()["merkle_root"]

        print()
        print(f"AFTER   target admitted       {after_target['admitted']}  "
              f"({after_target.get('reason')})")
        print(f"AFTER   claim  admitted       {after_claim['admitted']}  "
              f"({after_claim.get('reason')})")
        print(f"AFTER   first_divergent_node  {after_claim.get('first_divergent_node')}")
        print(f"AFTER   names the real cause  "
              f"{after_claim.get('first_divergent_node') == target}")
        print(f"AFTER   route admissible      {route_after['admission']['admitted']}")
        print(f"AFTER   merkle_root           {root_after}")
        print(f"AFTER   root moved            {root_after != root_before}"
              f"   <- expected False: the root commits to claims, not to disk")

        result = {
            "schema": SCHEMA_TAMPER,
            "merkle_convention": g.receipt()["merkle_convention"],
            "changed_artifact": f"{g.nodes[target].label}.payload.genes[TAZ].well",
            "change": "E06 -> E07",
            "bytes_changed": 1,
            "before": {
                "claim_admitted": before["admitted"],
                "claim_evidence_level": before.get("evidence_level"),
                "merkle_root": root_before,
            },
            "after": {
                "tampered_node_admitted": after_target["admitted"],
                "tampered_node_reason": after_target.get("reason"),
                "dependent_claim_admitted": after_claim["admitted"],
                "dependent_claim_reason": after_claim.get("reason"),
                "first_divergent_node": after_claim.get("first_divergent_node"),
                "first_divergent_node_is_the_tampered_node":
                    after_claim.get("first_divergent_node") == target,
                "route_admissible": route_after["admission"]["admitted"],
                "merkle_root": root_after,
                "merkle_root_moved": root_after != root_before,
                "why_root_did_not_move": (
                    "The root is a commitment to the node records, i.e. to what the "
                    "graph CLAIMS. Editing bytes on disk without editing the record "
                    "does not change any claim, so the root is unchanged and correct. "
                    "This tamper is caught by recomputation instead. See ARM B for the "
                    "attack that does move the root."
                ),
            },
            "assertions": {
                "A_tampered_node_rejected": after_target["admitted"] is False,
                "A_rejection_propagated_untouched": after_claim["admitted"] is False,
                "A_cause_named_precisely":
                    after_claim.get("first_divergent_node") == target,
                "A_root_correctly_unmoved": root_after == root_before,
            },
        }
    finally:
        with open(atom, "wb") as fh:
            fh.write(original)

    # ---------------------------------------------------------------- ARM B
    # The cover-up: change the bytes AND repair the record so recomputation
    # passes. This is what a careful adversary would actually do.
    banner("TAMPER TEST -- ARM B: the cover-up (repair the record too)")
    from fcg import Node, sha256_bytes  # noqa: E402

    victim = g.nodes[target]
    forged_digest = sha256_bytes(tampered)
    forged = Node(
        label=victim.label, kind=victim.kind, layer=victim.layer,
        content_digest=forged_digest,
        inputs=list(victim.inputs),
        custody=dict(victim.custody),
        recompute=dict(victim.recompute),
        claim=victim.claim,
    )
    forged_id = forged.node_id

    print(f"original node_id  {target}")
    print(f"forged   node_id  {forged_id}")
    print(f"node renamed      {forged_id != target}"
          f"   <- the id IS the hash of the record; you cannot edit without renaming")

    with open(atom, "wb") as fh:
        fh.write(tampered)
    forged_atom = os.path.join(g.root, "atoms", forged_digest.split(":", 1)[1])
    with open(forged_atom, "wb") as fh:
        fh.write(tampered)
    try:
        # splice the forged node in place of the original
        del g.nodes[target]
        g.nodes[forged_id] = forged
        for n in g.nodes.values():
            n.inputs = [forged_id if i == target else i for i in n.inputs]

        forged_root = g.receipt()["merkle_root"]
        forged_target_v = g.admit(forged_id)

        print(f"recomputation     {'PASSES' if forged_target_v['admitted'] else 'fails'}"
              f"   <- the cover-up defeats check one")
        print(f"merkle_root       {forged_root}")
        print(f"root moved        {forged_root != root_before}"
              f"   <- and is caught by check two")

        result["arm_b_coverup"] = {
            "description": "bytes altered AND record repaired so recomputation passes",
            "original_node_id": target,
            "forged_node_id": forged_id,
            "node_id_changed": forged_id != target,
            "recomputation_passes": forged_target_v["admitted"],
            "merkle_root": forged_root,
            "merkle_root_moved": forged_root != root_before,
        }
        result["assertions"]["B_coverup_defeats_recomputation"] = \
            forged_target_v["admitted"] is True
        result["assertions"]["B_coverup_moves_the_root"] = forged_root != root_before
        result["assertions"]["no_edit_survives_both_checks"] = (
            (after_target["admitted"] is False) and (forged_root != root_before)
        )
    finally:
        # unsplice
        for n in g.nodes.values():
            n.inputs = [target if i == forged_id else i for i in n.inputs]
        g.nodes.pop(forged_id, None)
        g.nodes[target] = victim
        with open(atom, "wb") as fh:
            fh.write(original)

    # rebuild clean
    restored_target = g.admit(target)
    restored_claim = g.admit(claim)
    root_restored = g.receipt()["merkle_root"]

    print()
    print(f"RESTORED target admitted      {restored_target['admitted']}")
    print(f"RESTORED claim  admitted      {restored_claim['admitted']}")
    print(f"RESTORED merkle_root          {root_restored}")
    print(f"RESTORED root returned        {root_restored == root_before}")

    result["restored"] = {
        "tampered_node_admitted": restored_target["admitted"],
        "claim_admitted": restored_claim["admitted"],
        "merkle_root": root_restored,
        "merkle_root_returned_to_original": root_restored == root_before,
    }
    result["assertions"]["clean_rebuild_readmits"] = (
        restored_claim["admitted"] and root_restored == root_before
    )
    result["pass"] = all(result["assertions"].values())
    result["canonical_run_modified"] = False

    with open(OUT, "w") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)

    banner("VERDICT")
    for k, v in sorted(result["assertions"].items()):
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    print()
    print(f"  OVERALL  {'PASS' if result['pass'] else 'FAIL'}")
    print(f"  written  {OUT}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
