# Protein Hinge Video Script

Target length: 90 seconds.

## Shot List

1. Open `http://127.0.0.1:8787/`.
2. Switch to Figure and show the cell-perturbation restoration figure.
3. Show the Verify tab with `phase_1_axis_claim`.
4. Switch to Browse and show the 62-node evidence table.
5. Switch to SQL and run the tractability query.
6. Switch to Prove and click `RE-VERIFY THE ROOT`.
7. Click `TAMPER WITH ONE NODE, THEN RE-VERIFY`.
8. End on the mismatch and first divergent node.

## Narration

Protein Hinge is a compact evidence ledger for a phenotype-first repurposing
hypothesis. The point is not just to show a ranking; it is to show exactly what
evidence the ranking rests on and whether another scientist can reproduce the
custody chain.

The scientific figure is the main result. ADA is the selected shifted
perturbation. The q95 reference threshold is shown, then 50 candidate profiles
are ranked by how much closer they sit to the reference phenotype than the ADA
perturbation. The top candidate is desonide, with a restoration score of about
0.50. This is a processed morphology distance benchmark, not a claim of
measured rescue.

Here the dashboard opens on a specific claim. The claim has a node id, a content
digest, a stated ceiling, and a list of upstream records. Some sources are
recomputed because the bytes are present; larger public records are committed by
origin digest, which is shown explicitly rather than hidden.

The Browse tab shows the whole package: 62 nodes across sources, derivations,
and claims. The SQL tab lets us query the local database directly. This example
shows the tractability check: EGFR is the positive control with chemistry, while
the consensus genes are recorded as undrugged in this search.

Now the important part: the Prove tab rebuilds the Merkle root in the browser.
It hashes every stored node record, rebuilds the RFC 6962 tree, and compares it
with the published root. The result matches.

Finally, we tamper with one record in memory. The rebuilt root moves, the
published root no longer matches, and the dashboard names the first divergent
node. That is the demo: a phenotype-first hypothesis with an auditable evidence
chain and visible tamper failure, without claiming treatment, efficacy, or a
legal FTO opinion.

## Exact Local Commands

```bash
python3 db/build_db.py
node site/verify_test.js
python3 scripts/make_cell_perturbation_figure.py
python3 db/serve.py 8787
```

Open `http://127.0.0.1:8787/`.

## Screenshot Assets

- Scientific figure: `../figures/cell_perturbation_restoration.png`
- Claim receipt: `../output/playwright/01-verify-claim-receipt.png`
- Evidence table: `../output/playwright/02-browse-evidence-posture.png`
- SQL setup: `../output/playwright/03-sql-tractability-query.png`
- SQL result: `../output/playwright/03-sql-tractability-results.png`
- Root proof: `../output/playwright/04-prove-root-pass.png`
- Tamper failure: `../output/playwright/05-tamper-root-fail.png`
