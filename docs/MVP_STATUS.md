# Protein Hinge MVP Status

Date: 2026-08-13

## What Works

- Local browser dashboard served from `site/` with no application backend.
- SQLite projection rebuilds deterministically from `fcg/store/`.
- Browser verifier recomputes all 62 Merkle leaves from stored node records.
- Scientific cell-perturbation figure shows the selected ADA perturbation,
  reference threshold, 50 ranked candidates, restoration scores, and pinned
  input hashes.
- Elvis component shows a disease-first prescripted Barth syndrome validation
  case and a conservative live ClinicalTrials.gov probe.
- GAP lane spec is incorporated as `docs/GAP_LANE_SPEC.md`; current rules are
  implemented in `gap/rules.py`, with no fuzzy target matching and an explicit
  `THERAPEUTIC_RECOMMENDATION` refusal.
- OpenAI fan-out uses the local ignored `.env`; each subagent, the model, and
  the integration record are stored as FCO JSON and projected into SQLite.
- Current inclusion route replays to the current Merkle root.
- Superseded science-only route is shown as stale rather than falsely checked
  against the FTO-extended root.
- Tamper demo edits one node record in memory and shows the root mismatch plus
  the first divergent node.
- FTO lane reports registry status and refuses to emit `FTO_OPINION`.

## Demo Path

```bash
python3 db/build_db.py
node site/verify_test.js
python3 fto/fto.py
python3 scripts/make_cell_perturbation_figure.py
python3 gap/ingest_gap.py
python3 scripts/run_openai_fanout.py --env-file .env --model gpt-4.1-nano --run-id 20260813Tfanout-elvis --max-workers 4
python3 scripts/build_agent_fanout_graph.py
python3 db/serve.py 8787
```

Open:

```text
http://127.0.0.1:8787/
```

## Claims We Can Make

- Protein Hinge is a hash-pinned evidence ledger over a small phenotypic
  repurposing hypothesis and its clearance-search record.
- The browser can independently rebuild the Merkle root from node records in
  the local SQLite projection.
- The demo distinguishes recomputed evidence from origin-attested evidence.
- A one-character record edit changes the rebuilt root and identifies the first
  divergent node.
- The FTO lane is a reproducible search record, not legal advice.
- The Elvis prescripted case marks elamipretide in Barth syndrome as
  `NOT_A_GAP` because it is already tried/covered in the validation landscape.
- OpenAI subagent outputs are custody objects in this repo; the API key is not
  committed or hashed into the graph.
- The GAP lane can grade prescripted rows by deterministic first-match rules
  G000-G008 and can refuse therapeutic recommendation output.

## Claims To Avoid

- Do not claim therapeutic efficacy.
- Do not claim measured biological rescue.
- Do not claim a legal freedom-to-operate opinion.
- Do not claim the full source ingest is self-contained in the received zip.
- Do not claim Convoke data was incorporated; the registry is documented as not
  wired in this package.
- Do not claim the live Elvis option performs the full Open Targets -> Convoke
  -> ClinicalTrials -> openFDA join. It currently probes ClinicalTrials.gov and
  abstains from full gap grading.

## Known Caveats

- The received origin artifact was named `biocustody.zip`; this published repo
  is Protein Hinge.
- Internal schema names and database filenames keep the `biocustody` prefix for
  compatibility with the committed records and dashboard.
- The source builders reference `HACKDAY_STATE.yaml`, which was not included in
  the received zip. The self-contained reproducible path is the committed
  store, SQLite projection, browser verifier, and FTO refusal check.

## Screenshots

- `../figures/cell_perturbation_restoration.png`
- `../figures/agent_fanout_fco_graph.png`
- `../output/playwright/01-verify-claim-receipt.png`
- `../output/playwright/02-browse-evidence-posture.png`
- `../output/playwright/03-sql-tractability-query.png`
- `../output/playwright/03-sql-tractability-results.png`
- `../output/playwright/04-prove-root-pass.png`
- `../output/playwright/05-tamper-root-fail.png`

## Small Partner Data Pulled Locally

- `../data/partner/candidate_ranking.csv`
- `../data/partner/state_model.json`
- `../data/partner/perturbation_state.json`
- `../data/partner/evaluation.json`

Each file is hash-checked by `scripts/make_cell_perturbation_figure.py` before
the figure is rendered.

## Presentation Materials

- `../docs/PLAIN_LANGUAGE_BRIEF.md`
- `../docs/AI_PRESENTATION_BRIEF.json`
- `../docs/FCO_FCG_DESIGN_CITATIONS.md`
- `../docs/ELVIS_COMPONENT.md`
- `../docs/GAP_LANE_SPEC.md`
