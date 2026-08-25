# NewInML @ NeurIPS 2026 — what's needed before Aug 29

**Deadline: 29 August 2026.** Today is 24 August. **Five days.**

## The venue's hard requirements

Source: <https://newinml.github.io/NewInML2026NeurIPS/>

| Requirement | Detail |
|---|---|
| **What is submitted** | A written **paper** — not a poster, not an abstract |
| **Length** | **2–8 pages excluding references**, NeurIPS 2026 workshop template |
| **Review** | **Double-blind** — full anonymisation required |
| **Platform** | OpenReview |
| **Eligibility** | Open to anyone who has **not** yet published at a top ML conference (NeurIPS, ICML, ICLR, …) |
| **Deadline** | **Aug 29, 2026** (submissions opened Jul 31) |
| **After** | Notification Sep 29 · camera-ready Nov 29 · workshop **Dec 11** |
| **Outcome** | Accepted papers get **poster** presentations; strongest get orals + awards |

**Clarifying the deliverable, since this caused confusion:** you submit **one
PDF**. The poster is built in Nov–Dec *only if accepted*. Code/artifacts are
**not** required by this workshop — the repo is optional supporting material.
The software we're building is not itself a submission; it is the instrument
that produces the numbers in the paper.

> Two things to verify, not assume: whether the deadline is AoE (anywhere on
> earth), and whether the "no prior top-ML publication" rule applies to **all**
> authors or just one. Byron may have prior publications; this decides the
> author list.

---

## A. Blocking — needs a human, cannot be done in Claude Code

| # | Item | Owner | Notes |
|---|---|---|---|
| A1 | **Get Byron's existing draft** | Elvis → Byron | He said he has most of it ready. **The single biggest unblock.** Everything below is cheaper once we see it. |
| A2 | **OpenReview account** | each author | Account creation can take time to be activated — do it today, not at the deadline |
| A3 | **Author list + eligibility check** | Byron | Does the eligibility rule bind all authors? |
| A4 | **Overleaf project from the NeurIPS 2026 template** | Byron or Elvis | Template link already circulated |
| A5 | **Click submit** | one author | Do it a day early; portals get slow at deadline |

---

## B. Anonymisation — the underestimated risk

**Our artifacts currently break double-blind.** This is not a formatting nit;
reviewers can desk-reject for it.

- [ ] Project name **"Protein Hinge"** appears in every figure, screenshot, and the DAG
- [ ] **"biobitworks"**, **"ElvisHan2022"**, repo URLs
- [ ] Dashboard branding baked into all screenshots
- [ ] The hackathon narrative (AWS event, participant role, event account) — identifying
- [ ] Acknowledgements section must be empty at submission
- [ ] If we link code: use an anonymised mirror (e.g. `anonymous.4open.science`), **never** the GitHub URL
- [x] AWS account id — already redacted from receipts and generators
- [x] Personal usernames removed from code

**Fastest path:** an anonymised figure set (rename the system to a neutral
placeholder in the DAG + regenerate screenshots from a re-branded local copy).
I can do this; it is a few hours, not a day.

---

## C. Paper content

Byron's draft may already cover much of this. Marked by who can move fastest.

| Section | Status | Who |
|---|---|---|
| Title + abstract | unknown — in Byron's draft? | Byron |
| Introduction / problem | likely drafted | Byron |
| Related work — TxGNN, Every Cure MATRIX, Healx, Citeline; plus provenance/audit literature | needs the ML-side citations | Byron + Elvis |
| **Method** — GATHER / GRADE / PROVE, the G000–G008 rules, enforced abstention, RFC 6962 custody | material exists in README + deck, needs compressing to ~1.5 pages | Elvis |
| **Results — errors prevented** | **numbers exist, table not yet written** | **Elvis (I can draft today)** |
| Limitations | must be explicit: one validation disease, no wet-lab validation, Convoke not wired, single-corpus snapshot | Elvis |
| Future work | conversation custody (FCO/FCG turn tracking); molecular validation (SS-31 folding, in vitro) | Elvis + Byron |
| Figures | workflow DAG (needs anonymising) + results table | Elvis |

### The results table — what we can honestly claim

Already measured, reproducible from the repo:

| Guard | Effect |
|---|---|
| Residue verification (FASTA lane) | **16 of 114** records a substituting pipeline would emit, caught as isoform-mismatched — plausible-but-wrong sequences |
| CNV filter (ClinVar lane) | **382** multi-gene copy-number events excluded from per-gene counts a naive pipeline would credit |
| Abstention accounting | **266** records declined, each with a named machine-readable reason |
| Output verification | 98 emitted sequences checked against wild-type: **98 correct, 0 incorrect** |
| Custody | single-byte edit detected client-side; root moves, first divergent node named |

**Recommended framing:** *naive pipeline vs. abstention-enforced pipeline —
silent errors prevented per lane.* That is a workshop-sized, defensible claim.

⚠️ **What we must not claim:** any therapeutic efficacy, that the gap-finding
generalises beyond the Barth validation case, or that the molecular work has
been done. The claim ceiling (`REPURPOSING_HYPOTHESIS`) belongs in the paper as
a *feature*, not a hedge.

**Worth building (half a day):** a `scripts/build_paper_metrics.py` that emits
this table from the repo, so every number in the paper is regenerable and
receipted. Fits the thesis exactly — say the word.

---

## D. Realistic five-day plan

| Day | Focus |
|---|---|
| **Aug 24 (today)** | A1 get Byron's draft · A2 OpenReview accounts · A3 confirm authors/eligibility · start results section |
| **Aug 25** | Method + results sections written; paper metrics script; decide what's cut |
| **Aug 26** | Anonymisation sweep: figures, screenshots, all naming |
| **Aug 27** | Full assembly in the template; check page limit (2–8 excl. refs); limitations + future work |
| **Aug 28** | Read-through for anonymity leaks; internal review; **submit** |
| **Aug 29** | Buffer only — do not plan to use it |

---

## E. Cut list, if time runs short

Cut in this order — each keeps the paper coherent:

1. Conversation custody as a *measured* contribution → move to Future Work **(already assumed cut)**
2. The Cell Painting / phenotype lane → one paragraph, cite as part of the system
3. The four-audience (patient/provider/policymaker/payer) framing → one sentence in the discussion
4. The UI redesign → drop entirely; it is not an ML contribution
5. Any molecular content → Future Work

**Never cut:** the measured results table, the limitations section, or the
anonymisation pass.
