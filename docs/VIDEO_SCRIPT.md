# Protein Hinge Video Script

Target length: ~3.5 minutes. Two acts: the workflow slide, then the live demo.
Tabs deep-link (`#elvis`, `#omics`, `#figure`, `#verify`, `#prove`) so shots
can be pre-staged as bookmarks.

## Act 1 — The workflow (~50s, over figures/workflow_dag.svg)

> One input: the name of a rare disease. One output: a graded table of
> drug–disease pairings, each row carrying the rule that graded it and a
> receipt you can verify yourself. In between — five questions, a rulebook,
> and a ledger.
>
> Five evidence lanes, one question each, all hitting real public APIs. Open
> Targets GraphQL: what biology is broken? NCBI ClinVar, pulled through
> E-utilities and staged into AWS HealthOmics — via boto3, S3, and IAM:
> do patients really carry pathogenic variants in these genes?
> 355 gene-specific records say yes. ClinicalTrials.gov's REST API: has this pairing been
> tried? openFDA: is the drug approved? Convoke is dashed out — listed,
> deliberately not wired, and we say so.
>
> All five feed a rulebook of plain Python — no framework, no model in the
> loop: GAP, NOT-A-GAP, or ABSTAIN, with abstentions displayed at equal
> weight. The AI never decides; code decides.
>
> Underneath sits the ledger: every record SHA-256 content-addressed into an
> RFC 6962 Merkle tree, projected into SQLite, and verified client-side — the
> dashboard is a single HTML page running sql.js in WebAssembly, so the tamper
> check happens in your browser, not on our server. Change one byte of
> evidence and the root moves in front of you.
>
> So the output isn't a ranking asking to be believed — it's a table where
> every cell can defend itself.

## Act 2 — The demo

### Beat 1 — Disease Search (~40s) — `#elvis`

DO: type "Barth syndrome", click **Show Known Case**, hover row 1; then click
**Check Live Trials**.

> Start where a clinician or a BD team starts: a disease name. Barth
> syndrome. Four rows come back — and look at row one. Elamipretide, graded
> NOT-A-GAP by rule G004: a trial already pairs this drug with this disease.
> That's the validation case. A naive repurposing tool would "discover"
> elamipretide and present the incumbent as a breakthrough. Ours refuses —
> and shows the three NCT trial IDs proving why. Notice the abstention
> counter beside the results: always on screen. When this system doesn't
> know, it says so at the same volume.
>
> And this button is live — querying ClinicalTrials.gov right now, and
> honestly labeling itself a trial probe, not a full gap grading.

### Beat 2 — AWS HealthOmics (~25s) — `#omics`

DO: open the HealthOmics tab, point to the evidence table, click
**CHECK LIVE STORE STATE**.

> The genetic second opinion. We pulled every pathogenic variant ClinVar
> reports for our eight genes — 355 gene-specific records, every query
> digest-recorded, after throwing out 287 whole-chromosome events that a
> naive pipeline would have counted. Look at TAFAZZIN: 100 pathogenic
> records, top condition 3-Methylglutaconic aciduria type 2 — that *is*
> Barth syndrome. The genetics independently agrees with the disease
> biology, and four of the eight genes honestly show zero.
>
> And this evidence lives in AWS: the subset and its provenance are uploaded
> digest-keyed to the account's HealthOmics S3 bucket, and we launched our
> own VEP annotation run on the account's HealthOmics workflow — watch the
> live probe list it. One more thing: the event account denies the
> deprecated annotation-store API by service control policy, and instead of
> hiding that, the probe records the denial as a receipt, right under the
> working runs. In this system, even "denied" is a first-class answer.

### Beat 3 — Cell Evidence (~25s) — `#figure`

> The science lane: Cell Painting morphology from the public JUMP dataset. A
> genetic perturbation pushes cells away from the reference state; fifty
> candidate compounds are ranked by how far back toward reference they move
> the phenotype. This is a distance benchmark on real processed profiles —
> and the label says exactly what it is: predicted counter-perturbation, not
> measured rescue.

### Beat 4 — Evidence Receipt (~25s) — `#verify`

DO: search `phase_1_axis_claim`.

> Now the part no other team has. Pick any claim — here's the core scientific
> one. It has a node ID, a content digest, a claim ceiling, and its full
> upstream chain: every source marked RECOMPUTED — we hold the bytes — or
> COMMITTED — we hold a digest captured at origin. That distinction is the
> honesty of this system. Most demos hide it. We render it.

### Beat 5 — Tamper Check (~35s) — `#prove`

DO: click **RE-VERIFY THE ROOT**; after the pass, click
**TAMPER WITH ONE NODE, THEN RE-VERIFY**.

> Finale. This button doesn't trust our published root — it re-hashes all 62
> records in your browser, rebuilds the Merkle tree, and compares. It
> matches.
>
> Now we cheat. One byte of one record, changed in memory... re-verify... and
> the root moves. The dashboard names the first divergent node. That's the
> whole thesis in one click: anyone can join four databases and rank drug
> pairings. What nobody else hands you is evidence that can't be quietly
> edited — verified on your machine, not ours.

### Close (~10s)

> Rare disease is the wedge, but any disease ID runs the same pipeline.
> Patients get trials worth asking about, providers get receipts, payers and
> policymakers get audit trails. Same table, same evidence, four audiences.

## Cutting to a shorter cap

If the submission caps at ~2:30: drop Beat 3 (cell evidence — the deck slide
covers it), merge Beat 4 into Beat 5 ("every claim carries a receipt — and
here is what happens when someone edits one"), and trim Act 1 to its first
and last paragraphs. That lands near 2:20.

## Fallbacks

- Conference wifi: the Known Case path is fully offline — skip the live
  clicks and say "the live probe also runs against ClinicalTrials.gov, but
  everything you're seeing is reproducible offline."
- HealthOmics credentials not wired: the abstention display **is** the
  feature; present it as scripted above.

## Exact Local Commands

```bash
python3 db/build_db.py
node site/verify_test.js
python3 scripts/build_clinvar_evidence.py
python3 scripts/build_fasta_lane.py
python3 scripts/healthomics_preflight.py
python3 scripts/run_healthomics_workflow.py # S3 upload + VEP run (needs .env creds)
python3 db/serve.py 8787
```

Open `http://127.0.0.1:8787/`.

## Screenshot Assets

- Workflow DAG: `../figures/workflow_dag.svg`
- Scientific figure: `../figures/cell_perturbation_restoration.png`
- Agent FCO graph: `../figures/agent_fanout_fco_graph.png`
- Null comparison: `../figures/null_hypothesis_comparison.png`
- Claim receipt: `../output/playwright/01-verify-claim-receipt.png`
- Evidence table: `../output/playwright/02-browse-evidence-posture.png`
- SQL result: `../output/playwright/03-sql-tractability-results.png`
- Root proof: `../output/playwright/04-prove-root-pass.png`
- Tamper failure: `../output/playwright/05-tamper-root-fail.png`
- HealthOmics tab: `../output/playwright/07-healthomics-tab.png`
- Disease Search: `../output/playwright/08-disease-search.png`
