# Handoff — `healthomics-lane` → `main`

**Branch:** `healthomics-lane` on `ElvisHan2022/protein-hinge`
**10 commits ahead of `main`** · 55 files · +5,063 / −459
**Nothing existing was deleted or rewired.** Every change is additive, a
correction to something that had become untrue, or a bug fix.

Two things run that did not before: a **live AWS HealthOmics workflow run**,
and **`node site/verify_test.js` on Windows**.

---

## 1. New lanes (the "what are we missing" answer)

### AWS HealthOmics — evidence in the cloud, honestly scoped
`scripts/build_clinvar_evidence.py` · `scripts/run_healthomics_workflow.py` ·
`scripts/healthomics_preflight.py` · `/api/healthomics` · dashboard tab

- **364 gene-specific pathogenic ClinVar records** for the eight consensus
  genes, every query URL and response digest recorded.
- **382 multi-gene copy-number events excluded** rather than counted. Whole-arm
  deletions were inflating per-gene totals (PHB2 was scoring on *Chromosome
  4q21 deletion syndrome*). Raw 746 → 364 after filtering; exclusions receipted
  per gene.
- TAFAZZIN: 109 records, top condition *3-methylglutaconic aciduria type 2* —
  Barth syndrome itself. Four of the eight genes honestly return **zero**.
- Evidence uploaded digest-keyed to the account's HealthOmics S3 bucket; our
  own **VEP annotation run completed** on the account workflow.
- The event account's SCP **denies the annotation-store API**. The probe
  records that denial as a receipt beside the working surface instead of
  hiding it.

### Sequence (FASTA) lane — bench-ready outputs
`scripts/build_fasta_lane.py` · `data/fasta/` · dashboard tab

Your folding / SS-31 work needs inputs; this produces them.

| Output | Contents |
|---|---|
| `consensus_genes.fasta` | 8 canonical sequences, all resolved from reviewed human UniProt |
| `variants.fasta` | **98 reconstructed variant sequences** — 40 missense, 58 truncating |
| `fasta_provenance.json` | every UniProt query URL + digest, plus the ClinVar input digest |

**The guard worth knowing about:** a substitution is applied *only* when the
wild-type residue ClinVar names matches the canonical sequence at that
position. That caught **32 records numbered against a different isoform** —
sequences that would have looked perfectly plausible in a FASTA file and
silently poisoned a folding run. 266 records abstained overall, each with a
named reason (116 no protein-level notation, 113 frameshifts not
reconstructable from a ClinVar title, 28 isoform mismatches, 3 out of range).
All 95 outputs were verified programmatically against their wild-types: 98
correct, 0 incorrect.

Claim ceiling `SEQUENCE_RECORD` — folding and assay *inputs*, not structures,
binding claims, or predictions of pathogenicity.

---

## 2. Bugs found and fixed

**`db/serve.py` was single-threaded.** One slow AWS probe (expired credentials
→ long retries) blocked *every* other request, including the dashboard's own
asset fetches. The page appeared to hang. Now `ThreadingTCPServer`; verified
assets serve while a slow API call is in flight. This would have failed live
on stage.

**`node site/verify_test.js` could not run on Windows.** It lifts the Merkle
implementation out of `index.html` by string markers written with bare `\n`,
but git's `autocrlf` checks the file out with CRLF, so the lift threw. The test
now normalises line endings first. It passes: **OVERALL PASS**, root matches
`d98a2972…`, tamper test still moves the root. Pre-existing — not introduced by
this branch.

---

## 3. Corrections (things that had become untrue)

| Where | Was | Now |
|---|---|---|
| `figures/workflow_dag.svg` | "642 records" | 364 |
| `workflow_dag.svg`, README, pitch deck, video script | "loaded into an annotation store" | staged into HealthOmics / S3 upload + VEP workflow run |
| README | implied `setup_healthomics.py` is the working path | states plainly it does **not** run in the event account; names `run_healthomics_workflow.py` as the one that does |
| `setup_healthomics.py` | looked current | `SUPERSEDED` header; retained for accounts that permit the annotation-store API |
| Dashboard preflight card | "expected user: elvish.an", "store: protein_hinge_clinvar" | workflows-visible / runs-recorded |
| Disease Search | target "TAZ" | **TAFAZZIN (TAZ)** — "TAZ" also means WWTR1, an unrelated protein |

The preflight was asserting an expected IAM username that the event account
never uses (it issues a shared `WSParticipantRole`), so
`identity_matches_expected` was permanently `false` and the UI advertised a
store that cannot exist.

---

## 4. Security / double-blind

**The AWS account id was committed in 4 receipt files** and visible in a
screenshot. House rule 5 says receipts mask everything; they did not. Now
redacted from the committed files *and* from all three generators (they emit
`account_last4`). Personal usernames removed from code.

⚠️ **Still outstanding before a double-blind submission:** the repo name,
"Protein Hinge", "biobitworks", the hackathon narrative, and the dashboard
branding all identify us. We need an anonymised artifact plan — happy to own
this.

---

## 5. Presentation material

- `figures/workflow_dag.svg` — the input→output DAG (evidence lanes, rules,
  custody, output; dashed = listed-not-wired).
- `docs/PITCH_DECK.md` — restructured as problem → approach → workflow → demo →
  differentiation → patient/provider/policymaker/payer implications.
- `docs/VIDEO_SCRIPT.md` — two acts (workflow slide, then five demo beats),
  with a cut-down to ~2:30 and offline fallbacks.
- `site/mockup.html` — **standalone UI redesign, no source code changed.**
  Clinical-calm direction (Abridge/Doximity), accountability as the page frame:
  verification bar first, receipt stepper beside results, abstentions at equal
  weight. Served at `/mockup.html`; shares zero code with the live dashboard.
- `CLAUDE.md` — builder guide: house rules, layout, gotchas, definition of done.
- New screenshots: `07-healthomics-tab.png`, `08-disease-search.png`.

---

## 6. Run it

```bash
py db/serve.py 8787                        # dashboard (threaded)
py scripts/build_fasta_lane.py             # UniProt + ClinVar variant FASTA (no AWS)
py scripts/build_clinvar_evidence.py       # refresh the ClinVar subset (no AWS)
py scripts/run_healthomics_workflow.py     # S3 upload + VEP run (needs .env creds)
py scripts/healthomics_preflight.py        # redacted status JSON
node site/verify_test.js                   # custody replay — now passes on Windows
```

Tabs deep-link: `#elvis` `#omics` `#fasta` `#verify` `#prove`.

Event credentials are temporary and expire — refresh from the portal into a
gitignored `.env` (plain `KEY=value`) when AWS calls fail with `ExpiredToken`.

---

## 7. Open questions for you

1. **Scope split for NeurIPS.** Recommendation: the ML paper is the
   accountability layer (deterministic rules + mandatory abstention +
   cryptographic custody, extended to conversation turns); the molecular work
   (SS-31 scoring, folding, MD, in vitro) is a separate bioRxiv paper cited as
   planned validation. Trying to make one paper do both weakens both.
2. **Conversation custody (FCO/FCG turn tracking)** — the piece you assigned
   each of us, and the paper's actual novelty for an ML audience. Ready to
   build it next; would like your design notes first.
3. **Remaining Track A items:** in vitro protocol drafts and the FDA
   information-readiness matrix. Both need a hard claim ceiling — we generate a
   scaffold your lab reviews; we do not issue lab instructions.
4. **`pepfunn` is not on PyPI** (GitHub install only); `metapredict` pulls in
   torch (~2.5 GB, CPU-fine). Real folding isn't local — the honest path is
   HealthOmics Ready2Run (AlphaFold/ESMFold), which reuses the AWS lane.
