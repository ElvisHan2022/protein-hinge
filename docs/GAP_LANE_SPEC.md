# BUILD SPEC — Rare Disease Repurposing Gap Finder
### Paste this into Codex as the working spec. Written August 13, 2026.

---

## 0. Three answers before anything else

**There is no protein folding in this project.** Nothing here predicts structure, docks a ligand, or reasons about conformation. The match is a **string join on gene identifiers**. Open Targets already did the biology and hands you a target list with an Ensembl ID, an HGNC symbol, an association score, and a tractability assessment. You join that symbol to a drug program's target field. That is the entire matching algorithm, and the hard part is name normalization rather than science.

**There is no database.** No Postgres, no vector store, no server. The store is a directory of files on disk, content-addressed by SHA-256, exactly as `fcg.py` already implements it. A "run" is a dated folder holding hashed raw responses, normalized CSVs, and a receipt. This is not a shortcut. It is the reason the pipeline is reproducible.

**Hosting is Streamlit reading those CSVs.** Local for the demo, Streamlit Community Cloud if there is time. Nothing else needs to run.

---

## 1. What the system does

Input a rare disease. Output a list of pairings between that disease and existing drug programs, where the biology implicates a target, a drug against that target already exists, and no registered trial pairs the drug to the disease.

Byron's existing repo already contains the canonical worked example: Barth syndrome, the TAZ/cardiolipin module, and elamipretide as the incumbent peptide. Use it as the validation case, since the answer is known and captured.

---

## 2. Where this sits in the existing repo

`fcg/` is the custody core and does not change. `fto/` is the freedom-to-operate lane and does not change. This build adds a third lane:

```
gap/
  normalize.py      target vocabulary reconciliation
  targets.py        Open Targets: disease -> targets
  programs.py       Convoke: targets -> drug programs
  priors.py         ClinicalTrials.gov: has this pair been tried
  rules.py          deterministic gap grading
  ingest_gap.py     builds the lane, attaches to the same Merkle root
  app.py            Streamlit
```

Every node this lane creates goes through `FCG.add_source_attested`, `add_derivation`, and `add_claim` from `fcg.py`. Same admission rule, same routes, same tamper test, one root over all three lanes.

**Claim ceiling for this lane is `REPURPOSING_HYPOTHESIS`.** The lane must refuse to emit anything reading as a therapeutic claim, following the pattern in `fto.emit_finding` where `FTO_OPINION` is declined out loud. Write the equivalent refusal for `THERAPEUTIC_RECOMMENDATION`.

---

## 3. The one thing Elvis unblocks

`registry_digests.json` currently records Convoke as `LISTED_NOT_WIRED`, with an explicit unblock condition: someone with access documents the endpoint, the query grammar, whether responses are stable or live, and the license on returned content.

Elvis holds Convoke access. Wiring Convoke is therefore the concrete contribution, and it converts a listed-not-wired registry into an admitted source. Document those four fields, set `CONVOKE_MCP_TOKEN` in `.env`, and change the status.

Endpoint: `https://mcp.convoke.bio/mcp`

Observed tracker schema: program name, companies, modality, target, route of administration, stage on a ladder from Preclinical through Approved.

---

## 4. The data model

No database. A run directory:

```
runs/2026-08-13/
  raw/                     one file per API response, named by sha256
  origin_digests.json      uri, sha256, bytes, http_status, corpus_date
  targets.csv              disease_id, ensembl_id, symbol, score, tractability_buckets
  programs.csv             program, company, modality, target_raw, target_symbol, stage
  priors.csv               disease_id, drug, nct_ids, n_trials
  candidates.csv           the output table
  abstentions.json         three counts plus reasons
  receipt.json             merkle root over the whole run
```

`corpus_date` is hashed into every node. The same query on a different day is a different node rather than a silently reused one. This convention already exists in `fto.add_search` and should be copied verbatim.

---

## 5. The joins, precisely

### J1. Disease to targets — Open Targets

MCP: `opentargets/platform-mcp`. Fallback: POST to `https://api.platform.opentargets.org/api/v4/graphql`.

The GraphQL shape is already proven in `registry_digests.json`:

```graphql
query T($id:String!){
  target(ensemblId:$id){
    id approvedSymbol approvedName biotype
    tractability{label modality value}
    drugAndClinicalCandidates{count}
    associatedDiseases(page:{index:0,size:5}){count rows{score disease{id name}}}
  }
}
```

For this lane the direction reverses: resolve the disease to an EFO or MONDO identifier, then pull `associatedTargets` with scores. Emit `targets.csv`.

**Filter rule:** keep targets above an association score threshold, and record the threshold in the node params so the run is reproducible.

### J2. Targets to programs — Convoke

This is the join that requires real work, and it is a **controlled vocabulary problem**.

Open Targets returns HGNC symbols: `TTR`, `SMN1`, `PARP1`, `PDCD1`, `CFB`. Convoke's tracker displays working names: `TTR`, `SMN1`, `PARP1`, `PD-1`, `Factor B`. The first three join directly. The last two do not.

Build `normalize.py` as a closed mapping with three outcomes and no repair:

| Outcome | Meaning | Handling |
|---|---|---|
| `EXACT` | strings match after casefold and whitespace strip | join |
| `MAPPED` | resolved through the hand-written alias table | join, stamp the alias used |
| `UNRESOLVED` | no confident mapping exists | **discard the row and count it** |

Never fuzzy-match. Never let a model guess a mapping. An unresolved target is an abstention, and abstention is a valid output. Seed the alias table by hand with the twenty or thirty pairs you actually encounter, and commit it as data rather than code.

### J3. Prior trial check — ClinicalTrials.gov

MCP: `cyanheads/clinicaltrialsgov-mcp-server`. Fallback: the v2 REST API already proven in `registry_digests.json` using `query.cond` and `query.intr`.

For each candidate pairing, query the disease as condition and the drug as intervention. Record NCT identifiers and the count.

**Record the caveat verbatim in the node**, since Byron already wrote the correct sentence: ClinicalTrials.gov registers trials rather than programs, so absence of a registered competitor is weak evidence of no competitor.

### J4. Incumbent check — openFDA

MCP: `Augmented-Nature/OpenFDA-MCP-Server`. Establishes whether a drug is approved and marketed, which sets the exclusivity boundary a second entrant must sit outside.

---

## 6. The gap rules

First match wins. Each stamps its identifier into the row. Plain Python, no model.

| Rule | Condition | Outcome |
|---|---|---|
| G000_UNRESOLVED_TARGET | target name did not reconcile | ABSTAIN |
| G001_NO_TARGET | disease has no target above threshold | ABSTAIN |
| G002_NO_PROGRAM | target has no program against it | ABSTAIN |
| G003_LOOKUP_FAILED | an API call failed or returned non-200 | ABSTAIN |
| G004_ALREADY_TRIED | a registered trial pairs this drug and disease | NOT_A_GAP |
| G005_GAP_APPROVED_DRUG | untried pairing, drug is approved elsewhere | GAP_HIGH |
| G006_GAP_LATE_STAGE | untried pairing, program is Phase 2 or 3 | GAP_MEDIUM |
| G007_GAP_EARLY | untried pairing, program is preclinical or Phase 1 | GAP_LOW |
| G008_UNCLASSIFIED | catch-all | ABSTAIN |

Ranking follows the stage ladder, since an approved drug is a stronger repurposing candidate than a preclinical one.

---

## 7. The abstention report

Three counts, displayed beside the results, never hidden:

1. diseases with no target above threshold
2. targets whose names did not reconcile
3. lookups that failed

Write these to `abstentions.json` and render them in the Streamlit page with equal visual weight to the candidate table.

---

## 8. Streamlit page

Single file. Disease input. Candidate table with columns for target, symbol, drug, company, modality, stage, rule fired, and prior trial count. The three abstention counts. One expanded example showing the full custody chain from the candidate row back to the hashed API response, using `FCG.custody_chain`.

The custody chain view is the demo moment. It is the thing no other team will have.

---

## 9. Build order

1. `normalize.py` with the alias table and the three outcomes. Test it on ten hand-written pairs before touching any API.
2. `targets.py`, `programs.py`, `priors.py` in parallel. Each returns a DataFrame and writes its raw response to `raw/` with a digest.
3. `rules.py`. Pure functions, no I/O, unit-testable.
4. `ingest_gap.py`. Wire the lane into FCG, produce a receipt, confirm the root covers all three lanes.
5. `app.py`.
6. Validation on Barth syndrome. Confirm elamipretide appears as `G004_ALREADY_TRIED` rather than as a gap, which proves the prior-trial filter works.

---

## 10. Explicitly not building

Protein structure or folding. Docking. Embeddings or vector similarity. Fine-tuning. A database server. Authentication. Multi-disease batch runs. Statistical significance testing. Any claim that a drug treats a disease.

---

## 11. The model's only job

One Bedrock call per candidate row, producing two sentences explaining why the pairing is plausible. The model receives the row as structured input and returns prose. It does not assign severity, does not decide inclusion, and does not resolve target names. Every decision upstream was made by rules that can be read.

If the model is unavailable, the pipeline still produces the full candidate table. The explanation column is the only thing that degrades.
