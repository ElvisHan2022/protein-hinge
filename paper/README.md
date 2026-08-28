# Paper — full draft for review

**Status: complete draft, not submission-ready.** Section 7 below lists what
must happen before it can be submitted. Deadline 29 August.

## What this is

A 2–8 page workshop paper arguing one narrow claim: a pipeline that must
*verify or decline* each input prevents a measurable class of silent error, and
here is the measurement. It does **not** claim the drug–disease pairings are
biologically correct — that needs wet-lab work we have not done, and claiming
it would be unpublishable.

## Build

```bash
cd paper
# neurips_2026.sty is NOT in this repo -- download it from the official
# Overleaf template and drop it beside main.tex
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

Keep `\usepackage{neurips_2026}` **without** `[final]` until acceptance —
`[final]` de-anonymises the paper.

## No number in this paper is typed by hand

`main.tex` opens with `\input{generated/results}`. That file is produced by the
pipeline:

```bash
python3 scripts/build_clinvar_evidence.py   # corpus
python3 scripts/build_fasta_lane.py         # sequences
python3 scripts/build_paper_metrics.py      # metrics + retired-value tracking
python3 scripts/build_paper_tex.py          # -> paper/generated/results.tex
```

Every figure, rate and table cell comes from `model_trace/paper_metrics.json`.
**If the compiled PDF disagrees with the pipeline, the PDF is stale.** This is
the same rule the project applies to its evidence, applied to its own write-up
— and it is not decoration: an earlier draft carried a rate that was wrong by
ten percentage points, and hand-typed numbers are how that survived.

## Guards on the paper itself

```bash
python3 scripts/check_cited_numbers.py --strict   # no superseded figure survives in prose
python3 scripts/check_anonymity.py --strict       # no identifying term in paper/
```

Both currently pass. Run them again after any edit.

## Current headline numbers

| | |
|---|---|
| G1 residue verification | 16 of 114 emitted sequences silently wrong — **14.0%** |
| G2 copy-number exclusion | 382 of 746 records misattributed — **51.2%** |
| Genes reduced to an honest zero | 3 of 8 (PGS1, PHB2, CHCHD3) |
| Cost of enforcement | sequence lane declines 266 of 364 records |
| Corpus reconciliation | 746 fetched = 364 kept + 382 excluded + 0 unavailable |

## What is deliberately in the paper that a reviewer might not expect

Section 5 reports **two defects in our own instrumentation**: a silent
100-record drop, and a headline rate overstated by ten points because the
pipeline mislabelled its own rejections. These are in rather than out because
omitting them would be the exact error the paper argues against, and because
they are the strongest available evidence that mechanical reconciliation beats
careful reading.

Section 6 states plainly that the entire G1 effect comes from **one gene**
(n=1, not 8), and that the rejected records are **recoverable** — a constant
+30 residue offset reconciles all 16 — so abstention here is the safe answer,
not the best one.

## 7. Before this can be submitted

Blocking, in rough order:

1. **Byron's draft merged.** He has most of a paper already; this is written to
   stand alone but should be reconciled with his framing (FCO/FCG as the
   method, this pipeline as the case study) rather than competing with it.
2. **Two citations verified by hand.** `references.bib` marks them
   `UNVERIFIED` — JMLR and NeurIPS proceedings do not register DOIs with
   Crossref, so the selective-classification references could not be
   machine-checked. Three others were verified against Crossref (title, first
   author, year and container all matched) and carry DOIs.
3. **Decide how to cite the team's prior custody work.** Those records are
   self-published and would identify the authors immediately. Either cite them
   in third person as prior art, or omit until camera-ready. This is a genuine
   double-blind hazard, not a formality.
4. **`neurips_2026.sty` obtained** and the page count checked against the 2–8
   page limit (excluding references).
5. **OpenReview accounts + author list**, including whether the
   "no prior top-ML publication" eligibility rule binds all authors or one.
6. **Anonymised artifact** for the reproducibility link, which currently says
   *withheld for review*.

## Known weaknesses a reviewer will probe

- **Small denominators.** Hundreds of records, one corpus snapshot, one
  disease family. Stated in Limitations.
- **We designed the guards and evaluated them ourselves.** Stated. The audit in
  Section 5 is offered as evidence that the residual is not zero.
- **Is the baseline a strawman?** Addressed in §4.1: the off condition is what
  you get by following each source's documentation, and only the ablated guard
  is disabled.
- **Isn't abstention free?** Addressed in §4.3 — the retention table is
  reported beside the benefit, because refusing everything would also score
  zero.
