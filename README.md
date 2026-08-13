# Protein Hinge

A hash-pinned evidence ledger for a small-molecule repurposing hypothesis in
Barth syndrome, and the freedom-to-operate record that sits beside it.

Two lanes, one Merkle root.

```
  SCIENCE LANE                          FTO LANE
  fcg/                                  fto/
  JUMP cpg0016 profiles                 ClinicalTrials.gov
  JUMP metadata                         openFDA label + NDC
  partner artifacts (pinned)            Open Targets tractability
        |                                     |
        +------------ one root ---------------+
        sha256:d98a2972e57a8e9c2f3111e224950d4ae74c65a6cfc18d064eb07014d4d589a4
```

## What the project is

Elamipretide (SS-31) is a peptide. It got FDA accelerated approval for Barth
syndrome in September 2025, and it is a daily subcutaneous injection that does
not cross the blood–brain barrier.

The question is whether a **small molecule** exists that pushes cells in the
direction opposite to the cardiolipin/cristae genetic lesion. Not a peptide
mimic — SS-31 is not in the compound library and is never a comparator. The
pipeline compares compounds against the *genetic lesion*, using a consensus
axis built from eight independent knockouts rather than any single gene.

The claim ceiling is `REPURPOSING_HYPOTHESIS` and it is enforced in code.
**Predicted counter-perturbation is not measured rescue.**

## Run it

```bash
python3 db/build_db.py        # rebuild the SQLite projection from fcg/store/
node site/verify_test.js      # replay browser verification headlessly
python3 fto/fto.py            # registry status + the FTO_OPINION refusal
python3 db/serve.py 8787      # serve the local browser demo
```

Open `http://localhost:8787` after starting the demo server.

Recording-ready materials:

- [MVP status](docs/MVP_STATUS.md)
- [Pitch deck document](docs/PITCH_DECK.md)
- [Video script](docs/VIDEO_SCRIPT.md)
- [Plain-language brief](docs/PLAIN_LANGUAGE_BRIEF.md)
- [AI presentation brief](docs/AI_PRESENTATION_BRIEF.json)
- [Disease search component](docs/ELVIS_COMPONENT.md)
- [FCO/FCG design citations](docs/FCO_FCG_DESIGN_CITATIONS.md)
- [Cell perturbation scientific figure](figures/cell_perturbation_restoration.png)
- [OpenAI fan-out FCO graph](figures/agent_fanout_fco_graph.png)
- [Null hypothesis comparison figure](figures/null_hypothesis_comparison.png)
- [Screenshots](output/playwright/)

## Disease Search + Agent FCO Demo

The dashboard now has two additional recording surfaces:

- `Disease Search`: disease-first rare disease repurposing finder. Prescripted Barth
  syndrome data works offline. The live option probes ClinicalTrials.gov and
  abstains from full gap grading until Open Targets and Convoke joins are
  wired.
- `GAP`: deterministic rare-disease gap grading lane under
  [GAP_LANE_SPEC.md](docs/GAP_LANE_SPEC.md). The current prescripted run emits
  `targets.csv`, `programs.csv`, `priors.csv`, `candidates.csv`,
  `abstentions.json`, and `receipt.json`.
- `AGENTS`: OpenAI fan-out receipts. Each subagent response is an FCO, the
  OpenAI model is an FCO, and the integration record tying those outputs into
  Protein Hinge is an FCO. These objects are projected into `fco_object` and
  `fco_edge` tables in the local SQLite database.
- `MODEL TRACE`: OpenAI and local-model trace surface. OpenAI ran the bounded
  subagent fan-out. Local Ollama models are inventoried by size and explicitly
  marked as available runtimes, not scientific data generators.
- `LOCAL JSON BEFORE WRITEBACK`: SeedGraph/FCO/Watchtower writeback candidates
  are saved locally in `docs/deferred_writeback_candidates.jsonl` and
  `model_trace/deferred_writeback_packet.json`. No live KG writeback is
  performed by this repo update.
- `@strands-agents/sdk` is installed and locked for the requested agent stack,
  though the verified fan-out path currently uses the OpenAI Responses API
  directly so it can write simple FCO receipts without extra runtime coupling.

Run the bounded fan-out only from a local ignored `.env`:

```bash
python3 scripts/run_openai_fanout.py --env-file .env --model gpt-4.1-nano --run-id 20260813Tfanout-elvis --max-workers 4
python3 scripts/build_agent_fanout_graph.py
python3 gap/ingest_gap.py
python3 scripts/build_model_trace.py
python3 scripts/build_regulatory_coverage.py
python3 scripts/aws_preflight.py
python3 db/build_db.py
```

The key and key hash are not written to the repo.

## Regulatory Coverage

Ingested and incorporated:

- ClinicalTrials.gov: Barth syndrome, elamipretide, and cardiolipin queries.
- openFDA: elamipretide label and NDC records.

Listed but not incorporated in this MVP:

- FDA orphan designation database: public web form, not captured as a stable
  reproducible source.
- European Medicines Agency EPAR / European drug approval data.
- Japan PMDA drug approval data.
- Full approved-drug coverage across FDA, Europe, and Japan.

The dashboard should describe these as future work unless source records and
receipts are added.

The dashboard `Regulatory Map` tab renders this boundary directly from
`model_trace/regulatory_coverage.json` plus the local registry tables, so the
demo can answer "what drug evidence is actually incorporated?" without
implying Europe/Japan/full-approved-drug coverage.

The received zip includes source builders (`fcg/ingest.py`,
`fcg/tamper_test.py`, and `fto/ingest_fto.py`), but those scripts reference a
local `HACKDAY_STATE.yaml` that was not included in the artifact. The committed
store, database projection, FTO refusal check, and browser verifier are the
self-contained reproducible path in this repo.

When the full ingest inputs are present, running `ingest.py` twice should
produce the same root. Timestamps are pinned to the observation date rather
than wall clock, because a node id is the hash of the node body and a live
clock would rename the whole graph on every run.

## The three rules

Applied identically at every depth. That identical application is what
"fractal" means here; it is not decoration.

**R1 — admit iff recomputes.** A node is admitted only if every input is
admitted and its own bytes recompute to its recorded digest.

**R2 — reject, do not annotate.** A node that fails R1 is rejected, not
admitted-with-a-warning. Rejection propagates to every descendant.

**R3 — route-comparable to the first divergent node.** "What broke" is answered
with a node id, not with a shrug.

## Two kinds of source, never conflated

`add_source_local` holds the bytes. Evidence level **RECOMPUTED**.

`add_source_attested` holds only a digest captured at the point of origin — the
honest record for a 13 MB parquet on someone else's S3 bucket. It asserts: at
this instant, that URI served exactly these bytes. Anyone can re-fetch and
check. Evidence level **COMMITTED**, because we do not hold the bytes and
saying otherwise would be a lie.

35 of 41 science-lane sources are attested. All 13 JUMP plates and all 6
metadata files returned HTTP 200 at capture.

## The tamper test has two arms

A ledger that never rejects anything is decoration. There are exactly two ways
to alter this graph and both are tested.

**Arm A — change the bytes, leave the record.** Recomputation fails, the claim
three layers up is rejected without being touched, and the rejection names the
first divergent node. The Merkle root does *not* move, and that is correct: the
root commits to what the graph *claims*, not to what is on disk.

**Arm B — change the bytes and repair the record.** The cover-up. Recomputation
now passes. But a node id is the hash of its record, so repairing the record
renames the node, and renaming the node moves the root.

The point is the conjunction. Arm A trips recomputation. Arm B trips the root.
**No edit survives both.** All eight assertions pass.

## On the partner receipt

`biobitworks/aws-biopharma` publishes a Merkle receipt with six digests and a
root, but does not declare the tree convention. Standard families were tested —
RFC 6962, duplicate-last, carry-odd, sorted-pair, raw and hex concatenation —
and none reproduced the stated root.

This is not an accusation. Nothing suggests the root is wrong. It says the
receipt is missing one field, and that field is the difference between
COMMITTED and RECOMPUTED. `verify_receipt()` encodes exactly that: a receipt
with no declared convention returns `COMMITTED`, with the note that the root is
asserted rather than proven. Ours declares `rfc6962/sha256`, its leaf and node
hash construction, and its leaf order.

The fix on their side is four fields.

## The finding that most affects the project

All eight consensus genes return **zero** small-molecule tractability buckets
and **zero** drug or clinical candidates in Open Targets. EGFR, queried
identically as a positive control, returns five SM buckets and 82 candidates —
so the field works and the zeros are real.

This is the strongest argument for the method: you cannot run structure-based
design against a protein with no ligandable pocket, but a phenotype-first
ranking does not need one.

It is also the sharpest caveat on any result: there is no reference chemistry
against this module, so no positive-control compound exists to validate the
axis and no prior art exists to catch a wrong hit.

Both halves are in the graph, on the same node.

## Not legal advice

`fto/` produces a reproducible clearance *search record*, capped at
`CLEARANCE_SEARCH_RECORD`. It refuses to emit `FTO_OPINION` — that is a legal
conclusion issued by qualified counsel who signs their name to it. The level
exists in the enum so the code can decline it out loud rather than by omission.

See `fto/FTO_DESIGN.md`.

## Credentials

Never in this repo. `.env` only. Convoke is listed and deliberately not wired:
we do not hold `CONVOKE_MCP_TOKEN`, and a source whose query surface nobody has
documented cannot be recomputed by a third party, so it cannot be admitted.

## Data

Cell Painting Gallery / JUMP `cpg0016`, released **CC0 1.0 Universal**. Citation
is an ethical obligation rather than a license condition, and we honor it: the
JUMP dataset paper and Weisbart et al. 2024 for the Gallery.

CC0 on a morphological profile says nothing about rights in the molecule it
depicts. That is the trapdoor, and it is why the FTO lanes are tracked
separately.

## License

Code and documentation are released under Apache-2.0. See `LICENSE` and
`NOTICE`.
