# Debrief — what changed on `healthomics-lane`

**Branch:** `ElvisHan2022/protein-hinge` → `healthomics-lane` · 11 commits ahead
of `main` · 56 files · +5,200 / −459
**Nothing was deleted or rewired.** Every change is additive, a correction to
something that had become untrue, or a bug fix.
**Line-by-line detail:** `docs/HANDOFF_ELVIS_2026-08-24.md` (in the branch).

Two things run that did not before: a **live AWS HealthOmics workflow run**,
and **`node site/verify_test.js` on Windows**.

---

## 1. Two new lanes

**AWS HealthOmics is live.** 364 gene-specific pathogenic ClinVar records for
the eight consensus genes, every query URL and response digest recorded,
uploaded digest-keyed to the account's HealthOmics S3 bucket — and our own VEP
annotation run **COMPLETED** on the account workflow. The event account's
service control policy denies the annotation-store API; the dashboard records
that denial as a receipt beside the working surface rather than hiding it.

**The FASTA lane answers your top-three question.** `scripts/build_fasta_lane.py`
produces the inputs your folding and SS-31 work needs:

- 8 canonical sequences, all resolved from reviewed human UniProt
- **98 reconstructed variant sequences** — 40 missense, 58 truncating
- full provenance: every UniProt query URL + digest, plus the ClinVar input digest

Remaining two of your three (in vitro protocol drafts, FDA information-readiness
matrix) are scoped and next, both with a hard claim ceiling: we generate a
scaffold your lab reviews, we never issue lab instructions.

---

## 2. The finding worth your attention

A substitution is applied **only** when the wild-type residue ClinVar names
matches the canonical sequence at that position. That guard **caught 28 records
out of 123** with usable protein-level notation — records numbered against a
different isoform, which would have emitted perfectly plausible FASTA and
silently poisoned a folding run.

This is the paper's result in miniature: *enforced abstention prevents a
measurable, specific class of silent error.* Same shape as the CNV filter (382
whole-chromosome events excluded from what a naive pipeline counts) and the
terminated-trial distinction.

266 records abstained overall, each with a named machine-readable reason. All 98
emitted sequences were verified programmatically against their wild-types: 98
correct, 0 incorrect.

---

## 3. Two real bugs, both fixed

**The demo server was single-threaded.** One slow AWS probe (expired credentials
→ long retries) blocked *every* other request, including the dashboard's own
asset fetches — the page simply appeared to hang. Now `ThreadingTCPServer`,
verified serving assets while a slow call is in flight. **This would have failed
live on stage.**

**`node site/verify_test.js` could not run on Windows at all.** It lifts the
Merkle implementation out of `index.html` by string markers written with bare
`\n`, but git's `autocrlf` checks the file out with CRLF, so the lift threw.
Pre-existing — I confirmed by stashing my changes and reproducing it. Now
normalises line endings first and passes: **OVERALL PASS**, root matches
`d98a2972…`, tamper test still moves the root.

---

## 4. Corrections — claims that had become untrue

| Where | Was | Now |
|---|---|---|
| `workflow_dag.svg` | "642 records" | 364 |
| DAG, README, deck, video script | "loaded into an annotation store" | staged into HealthOmics / S3 upload + VEP run |
| README | implied `setup_healthomics.py` works | states plainly it does **not** run in the event account; names the script that does |
| Dashboard preflight | "expected user: elvish.an", "store: protein_hinge_clinvar" | workflows-visible / runs-recorded |
| Disease Search | target "TAZ" | **TAFAZZIN (TAZ)** — "TAZ" also means WWTR1, an unrelated protein |

The preflight asserted an IAM username the event account never issues (it hands
out a shared `WSParticipantRole`), so the identity check was permanently false
and the UI advertised a store that cannot exist.

---

## 5. Security / double-blind

**The AWS account id was committed in 4 receipt files** and visible in a
screenshot — house rule 5 says receipts mask everything; they did not. Now
redacted from the files *and* all three generators. Personal usernames removed
from code.

⚠️ This is the part I want to flag hardest: **the submission is double-blind and
our artifacts currently break it.** Repo name, "Protein Hinge", "biobitworks",
the hackathon narrative, dashboard branding. See the submission checklist.

---

## 6. Presentation material

- `figures/workflow_dag.svg` — input→output DAG (dashed = listed-not-wired)
- `docs/PITCH_DECK.md` — problem → approach → workflow → demo → differentiation
  → patient/provider/policymaker/payer
- `docs/VIDEO_SCRIPT.md` — two acts, five demo beats, cut-down to ~2:30
- `site/mockup.html` — **standalone UI redesign, zero source changes.** Clinical
  direction (Abridge/Doximity), accountability as the page frame: verification
  bar first, receipt stepper beside results, abstentions at equal weight
- `CLAUDE.md` — builder guide: house rules, layout, gotchas, definition of done
- New screenshots: HealthOmics tab, Disease Search

---

## 7. Where I'd like your input

1. **The paper's scope.** I'd argue NeurIPS gets the accountability layer
   (deterministic rules + enforced abstention + custody) with the measured
   errors-prevented result; the molecular work (SS-31 scoring, folding, MD,
   in vitro) goes to bioRxiv and is cited here as planned validation. One paper
   doing both weakens both — and the deadline makes the choice for us.
2. **Conversation custody (FCO/FCG turn tracking).** Ready to build, but with
   five days to the deadline I'd make it the Future Work section rather than a
   measured contribution. Send your design notes and I'll start after Aug 29.
3. **Your draft.** You mentioned having most of the paper ready — sharing it
   today is the single biggest unblock.

**Dependency notes:** `pepfunn` is not on PyPI (GitHub install only);
`metapredict` pulls in torch (~2.5 GB, CPU-fine). Real folding isn't local — the
honest path is HealthOmics Ready2Run (AlphaFold/ESMFold), which reuses the AWS
lane we already have working.
