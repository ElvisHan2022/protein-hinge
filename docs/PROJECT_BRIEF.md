# Project brief — what we built, what's real, what "finished" means

Written to reorient. Read the first two sections if nothing else.

---

## 1. What the platform is, in one paragraph

**Protein Hinge answers one question — "which existing drugs should already
have been tried against this rare disease, and why hasn't anyone?" — and makes
every part of that answer checkable by a stranger.** Five public evidence
sources are queried, each response is fingerprinted the moment it arrives, nine
readable rules (not a model) grade each drug–disease pairing as a genuine gap /
already tried / can't say, and every record is committed under a single
cryptographic root that a reader re-verifies **in their own browser**. The
product is not the ranking. The product is *a ranking you don't have to trust
us about.*

## 2. The honest state of it — the one thing to internalise

The system has two halves, and they are at very different maturity:

| Half | State |
|---|---|
| **Evidence + custody** (gather the facts, hash them, prove nothing changed) | **Real and live.** Queries hit real APIs, digests are recorded, the Merkle verification passes and catches tampering. |
| **Decision** (turn facts into a graded verdict for *any* disease) | **Runs end-to-end on one disease.** The rules are fully implemented and self-tested, but they execute against a prescripted fixture for Barth syndrome, not live input. |

Concretely: `gap/ingest_gap.py` reads `elvis_prescripted_demo.json`; the only
disease identifier in the codebase is a hardcoded `MONDO:0010526`. Open Targets
*is* queried live — but by **gene**, for druggability, in the FTO lane. **There
is no live disease → target resolution anywhere in the repo.**

That is the gap between "compelling demo" and "platform," and it is one
well-scoped piece of work (§5, step 1).

Nothing about this is hidden — the DAG carries the footnote, the dashboard
abstains on arbitrary input, and the live probe labels itself
`ABSTAIN_LIVE_TARGET_PROGRAM_JOIN_NOT_WIRED`. The honesty is the point. But it
does mean *end-to-end for arbitrary input is not yet true.*

---

## 3. What is actually built and running

**Custody core** (`fcg/`) — content-addressed store, RFC 6962 Merkle root over
62 records, client-side re-verification, tamper demonstration.
`node site/verify_test.js` → **OVERALL PASS** (fixed this week; it could not run
on Windows at all).

**Evidence lanes**

| Lane | Live? | What it produces |
|---|---|---|
| Open Targets (`fto/`) | live, by gene | tractability — all 8 consensus genes return **zero** small-molecule chemistry, EGFR positive control returns 5 buckets |
| ClinVar → AWS (`scripts/build_clinvar_evidence.py`) | live | **364** gene-specific pathogenic records, 382 multi-gene copy-number events excluded |
| ClinicalTrials.gov | live probe + captures | trial existence **with status and phase**, so terminated ≠ untried |
| openFDA | captures | approval status, label |
| JUMP Cell Painting | pinned artifacts | phenotype restoration ranking |
| Convoke | **not wired** | drawn dashed everywhere; no verifiable query surface |

**Sequence lane** (`scripts/build_fasta_lane.py`) — 8 canonical UniProt
sequences + **98 reconstructed variant sequences**, with the residue guard that
caught **32 isoform-mismatched records** out of 123.

**AWS HealthOmics** — evidence uploaded digest-keyed to S3; our own **VEP
annotation run COMPLETED** on the account workflow. Annotation-store API is
SCP-denied; the denial is recorded as a receipt.

**Dashboard** (`site/index.html`) — 12 tabs, single file, sql.js in WebAssembly,
threaded server (fixed this week: one slow AWS call used to freeze everything).
Plus `site/mockup.html`, a standalone redesign that changes no source.

**Decision layer** (`gap/rules.py`) — G000–G008 fully implemented with a
self-test. Sound logic; fixture-fed input.

---

## 4. Two tracks, and why they must not merge

| | **Track P — the paper** | **Track B — the biology** |
|---|---|---|
| Venue | NewInML @ NeurIPS 2026 | bioRxiv |
| Deadline | **Aug 29, 2026** | months |
| Claim | enforced abstention + custody prevents a measurable class of silent error | SS-31 / variant folding, in vitro validation |
| Needs | the numbers we already have | synthesis, cells, lab time |
| Status | ready to write | not started |

Track B is cited *inside* Track P as planned validation. One paper attempting
both weakens both, and the deadline makes the choice for us.

---

## 5. What "finished end-to-end" actually requires

Four steps, in dependency order. Only the first is hard.

**1. Live disease → target.** Resolve a disease name to an ontology ID, query
Open Targets for associated targets above a recorded threshold. This is the
missing link — everything downstream already exists. *~1 day. No blockers, no
credentials needed.*

**2. A drug-program source to replace the dashed box.** Convoke has no
verifiable query surface, so it fails our own admissibility rule. **ChEMBL is
the honest substitute** — open, documented, re-queryable by a third party, and
it answers exactly the needed question (target → drugs/mechanism, with
development phase). Un-dashes the box legitimately. *~1 day.*

**3. Wire the rules to live inputs** instead of the fixture, keeping the
prescripted case as a regression test. *~half a day.*

**4. Then the honest claim becomes:** type any rare disease, get graded rows
with receipts and real abstention counts. That is the platform.

**Independently useful, not on the critical path:** in vitro protocol drafts and
the FDA information-readiness matrix (Byron's remaining two of three);
conversation custody (FCO/FCG turn tracking) — the paper's future work and
genuinely novel; anonymised artifact set for double-blind.

---

## 6. What I need, and from whom

### From Byron

| # | Need | Blocks | Why it can't wait |
|---|---|---|---|
| B1 | **His paper draft** | all paper work | He says most is ready; everything else is guesswork until we see it. **Five days.** |
| B2 | **Author list + eligibility ruling** | submission | Does "no prior top-ML publication" bind all authors or one? |
| B3 | **FCO/FCG conversation-tracking design notes** | the novel contribution | He offered these; needed before building |
| B4 | **Convoke: is there a token, ever?** | §5 step 2 | If no, we adopt ChEMBL and stop deferring |
| B5 | **Scope ruling: platform or paper first?** | my next 5 days | Can't do both well before Aug 29 |

### From you (Elvis)

| # | Need | Blocks |
|---|---|---|
| E1 | **OpenReview account** | submission — activation can lag, do it today |
| E2 | **Fresh AWS credentials when they expire** | any live AWS probe; event creds are temporary |
| E3 | **Open the PR to `biobitworks/protein-hinge`** | Byron reviewing any of this |
| E4 | **ORCID, email, LinkedIn, bio blurb** | Byron's ask — yours to write (I can draft the blurb) |
| E5 | **Priority call on B5** | what I build tomorrow |

### From me — no blockers, buildable now

- `scripts/build_paper_metrics.py` — regenerates the paper's results table from
  the repo, so every number is reproducible and receipted
- The paper's **results + method sections** from existing measurements
- Anonymisation sweep for double-blind (figures, screenshots, naming)
- §5 steps 1–3 (live disease→target, ChEMBL, wire the rules)
- In vitro protocol drafts + FDA readiness matrix
- Conversation custody — *after* B3

### From nobody — genuinely blocked

Wet-lab validation, compound synthesis, and any efficacy claim. These are
Track B, they need Byron's lab, and no amount of code substitutes for them.

---

## 7. The single decision that matters this week

With five days to Aug 29, **Track P and §5 cannot both happen.** My
recommendation: **freeze the platform, write the paper.** The measurements
needed for a defensible workshop paper already exist; the platform work is
better done after notification (Sep 29), when it can inform the camera-ready
and the poster.

If the answer is "platform first," say so and I'll start with live
disease → target — but then the paper needs to be Byron's draft plus a results
section, and nothing more ambitious.
