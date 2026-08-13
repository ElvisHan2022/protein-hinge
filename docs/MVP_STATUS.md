# Protein Hinge MVP Status

Date: 2026-08-13

## What Works

- Local browser dashboard served from `site/` with no application backend.
- SQLite projection rebuilds deterministically from `fcg/store/`.
- Browser verifier recomputes all 62 Merkle leaves from stored node records.
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

## Claims To Avoid

- Do not claim therapeutic efficacy.
- Do not claim measured biological rescue.
- Do not claim a legal freedom-to-operate opinion.
- Do not claim the full source ingest is self-contained in the received zip.
- Do not claim Convoke data was incorporated; the registry is documented as not
  wired in this package.

## Known Caveats

- The received origin artifact was named `biocustody.zip`; this published repo
  is Protein Hinge.
- Internal schema names and database filenames keep the `biocustody` prefix for
  compatibility with the committed records and dashboard.
- The source builders reference `HACKDAY_STATE.yaml`, which was not included in
  the received zip. The self-contained reproducible path is the committed
  store, SQLite projection, browser verifier, and FTO refusal check.

## Screenshots

- `../output/playwright/01-verify-claim-receipt.png`
- `../output/playwright/02-browse-evidence-posture.png`
- `../output/playwright/03-sql-tractability-query.png`
- `../output/playwright/03-sql-tractability-results.png`
- `../output/playwright/04-prove-root-pass.png`
- `../output/playwright/05-tamper-root-fail.png`
