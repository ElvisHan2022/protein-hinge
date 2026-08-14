# Builder guide — Protein Hinge

Orientation for any builder terminal (Claude Code or human) working in this
repo. Read this before touching anything; the project has house rules that
matter more than code style.

## What this is

A disease-first rare-disease repurposing demo with a cryptographic evidence
trail. Input: a rare disease name. Output: existing drugs graded
GAP / NOT_A_GAP / ABSTAIN by deterministic rules, every claim traceable to
hashed source records, verified client-side in the browser. Full plain-language
story: top of `README.md`. Pitch arc: `docs/PITCH_DECK.md`.

## Current state (2026-08-13)

- Branch `healthomics-lane`, ahead of `main`. Do not push without asking.
- Dashboard works offline: committed `site/biocustody.db`, prescripted Barth
  syndrome case, live ClinicalTrials.gov probe.
- HealthOmics lane: ClinVar subset built (355 gene-specific records after
  CNV filtering, digests recorded) and **uploaded to the event's HealthOmics
  S3 bucket**; our VEP run launched on the account's workflow
  (`scripts/run_healthomics_workflow.py`). The event SCP denies the
  deprecated annotation-store API — the live probe records that denial as a
  receipt. Credentials: temporary event creds in gitignored `.env`
  (plain `KEY=value`, no `$Env:`), they expire — refresh from the event
  portal when AWS calls fail with ExpiredToken.
- Convoke: listed, deliberately not wired. Leave it that way unless a token
  and documented query surface both exist.

## Run it (Windows: use `py`, not `python3` — no python on PATH)

```powershell
py db/serve.py 8787                       # dashboard at localhost:8787
py db/build_db.py                         # rebuild SQLite from fcg/store/
node site/verify_test.js                  # headless verification replay
py scripts/build_clinvar_evidence.py      # refresh ClinVar subset (no AWS)
py scripts/healthomics_preflight.py       # redacted AWS/store status JSON
py scripts/setup_healthomics.py           # bucket + role + store + import (needs creds)
```

Dashboard tabs deep-link: `#elvis` `#omics` `#figure` `#verify` `#prove` etc.
Screenshots for the deck: headless Edge against those URLs (see
`output/playwright/`), or the checked-in captures.

## Layout

| Path | What it is |
|---|---|
| `fcg/` | Custody core: content-addressed store, RFC 6962 Merkle root, tamper test. Do not modify casually — node ids are hashes of records. |
| `fto/` | Freedom-to-operate lane. Refuses `FTO_OPINION` by design. |
| `gap/` | Gap-grading lane: `normalize.py` (closed alias table), `rules.py` (G000–G008), prescripted demo JSON, run artifacts. |
| `db/` | `build_db.py` projects the store into SQLite; `serve.py` serves `site/` + `/api/elvis` + `/api/healthomics`. |
| `site/index.html` | The whole dashboard: single file, vanilla JS, sql.js WASM. Tab pattern: nav `data-t="x"` ↔ `section#s-x` ↔ `initX()` hooked in `boot()`. |
| `scripts/` | Pipeline builders. Each writes a receipt JSON to `model_trace/` and mirrors it into `site/assets/`. |
| `data/healthomics/` | ClinVar subset TSV + query provenance digests. |
| `docs/` | Pitch deck, video script, plain-language brief, specs. Keep them consistent with the GATHER/GRADE/PROVE spine in `README.md`. |

## House rules (non-negotiable)

1. **Code decides, models phrase.** No LLM output may ever set a grade,
   resolve a target name, or pick a threshold.
2. **Abstain, never guess.** A failed lookup, unmappable name, or missing
   credential becomes a named abstention rendered at equal visual weight —
   not a silent empty result, not a fabricated value.
3. **Claim ceilings are enforced, not stylistic.** Science caps at
   `REPURPOSING_HYPOTHESIS`; FTO caps at `CLEARANCE_SEARCH_RECORD`. Never
   write copy implying treatment, efficacy, or measured rescue.
4. **Provenance or it didn't happen.** Anything fetched from outside gets its
   URL and response digest recorded. Scrapes that a third party cannot
   re-fetch are inadmissible.
5. **No secrets in the repo.** Credentials live in `.env` (gitignored) or
   `~/.aws`. Status JSONs must mask everything (see `masked()` in
   `scripts/aws_preflight.py`).
6. **Honest wiring.** If a source or feature is not integrated, say so in the
   UI and docs ("listed, not wired") rather than removing the mention or
   implying coverage.
7. **Timestamps:** pipeline nodes pin `corpus_date`, not wall clock — a live
   clock would rename the whole graph on every run.

## Gotchas

- `git` warns LF→CRLF on this machine; harmless, ignore.
- `fcg/ingest.py` and `fto/ingest_fto.py` reference a `HACKDAY_STATE.yaml`
  that is not in the repo; the committed store is the reproducible path.
- The dashboard loads sql.js and cytoscape from CDNs — offline demos need
  those cached or vendored.
- After editing `db/serve.py`, restart the server; after editing
  `site/index.html`, a browser refresh is enough (`Cache-Control: no-store`).
- `site/assets/*.json` are generated mirrors — edit the generator script in
  `scripts/`, never the asset by hand.

## Definition of done for any change

Dashboard loads, the affected tab renders real or honestly-abstained data,
`node site/verify_test.js` still passes, nothing secret is staged, and the
docs that mention the changed surface still tell the truth.
