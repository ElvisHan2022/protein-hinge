# Protein Hinge Origin Review

Date: 2026-08-13

## Origin

- Received artifact: `/Users/byron/Downloads/biocustody.zip`
- Extracted top-level folder: `biocustody/`
- Published repository name: `protein-hinge`

## Review Findings

- The origin artifact is visibly branded as BioCustody and describes a Barth
  syndrome small-molecule repurposing hypothesis.
- The artifact contains a complete committed FCG/FTO store, SQLite projection,
  static browser demo, and headless browser verifier.
- The source graph builders are not fully self-contained in the zip:
  `fcg/ingest.py`, `fcg/tamper_test.py`, and `fto/ingest_fto.py` require a
  `HACKDAY_STATE.yaml` file outside the extracted package.
- The downstream SQLite projection rebuilds from `fcg/store/` and passes its
  internal Merkle-root self-check.
- The original `site/verify_test.js` replayed superseded Merkle routes against
  the current FTO-extended root and used an obsolete tamper target. The verifier
  has been updated to distinguish current and stale routes and to use a
  deterministic record-level tamper target present in the current store.

## Publishing Decisions

- Visible project branding is now Protein Hinge.
- The internal schema prefix `biocustody.*` and database filename
  `biocustody.db` are retained to avoid changing committed node records or
  breaking the shipped browser demo.
- This repository is separate from the AWS Biopharma hackday repo and from the
  old local BioCustody repo.

## Verification Commands

```bash
python3 db/build_db.py
node site/verify_test.js
python3 fto/fto.py
```
