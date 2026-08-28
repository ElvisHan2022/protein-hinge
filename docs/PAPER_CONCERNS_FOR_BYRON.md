# Limitations and open concerns — paper draft

For Byron. Written 2026-08-28, against the draft that compiles to
`paper/main.pdf` (7 pages: 6 body + 1 references).

This is the list of things I would want a reviewer to catch me on, sorted by
how much damage each one does if it goes unaddressed. Items marked **DECISION**
need you; the rest are disclosures.

---

## 1. The headline G1 number rests on one gene

All 16 residue mismatches come from TAFAZZIN. A second gene (HADHA)
contributes more emitted sequences than TAFAZZIN does and produces zero
mismatches.

So the honest description of the G1 result is **n=1**, not n=8. What we
measured is one transcript-numbering convention disagreeing between two
sources, and we found it once. The paper says this in Limitations in exactly
those terms, and a reviewer will still push on it.

**Why I did not fix it:** adding genes means another live capture and another
corpus digest, and the disagreement may simply not recur — which would leave a
0/N result and no headline at all. I would rather ship the honest n=1 than
fish for a second instance under deadline.

**What would strengthen it:** either a second gene family that reproduces the
effect, or reframing G1 as a *case study* and letting G2 (which does vary
across 8 genes, 3 of them to zero) carry the generality claim.

## 2. The records we decline are recoverable, and we throw them away

A single constant offset of **+30 residues reconciles all 16 of them exactly**.
ClinVar numbers those variants against the longer TAFAZZIN transcript; the
UniProt canonical sequence is 30 residues shorter at the N-terminus.

This cuts both ways and I want you to see it clearly before a reviewer does:

- It *strengthens* the silent-error claim. The mismatches are real, systematic,
  and would have produced 16 confidently wrong FASTA files.
- It *weakens* the abstention claim. Abstaining is the safe move, not the good
  one. A better pipeline detects the offset and recovers all 16.

The paper concedes this outright in Limitations. I think conceding is correct —
the alternative is a reviewer finding it and concluding we did not look.

## 3. We designed the guards, chose the data, and graded our own work

There is no external benchmark here. The failures the guards catch are
failures we anticipated well enough to write a guard for. What the ablation
measures is *the value of enforcement given a correct precondition*. It says
nothing about how many preconditions we failed to think of.

Section 5 (the two defects we found in our own instrumentation) is the honest
evidence that that residual is greater than zero. It is also the part of the
paper I am least sure how a reviewer will read: as unusual rigour, or as an
admission that our numbers moved twice before submission. I lean toward
keeping it — removing it would be the exact failure the paper is about — but
it is your call whether to keep it as its own numbered section or fold it into
Limitations.

## 4. Small denominators, one snapshot, a live source

Rates come from hundreds of records, from one capture of one database. ClinVar
is live: two honest runs a day apart returned different totals. We pin a
capture date and publish the digest of the exact table used, which makes the
result reproducible but not stable.

Reviewers in ML will read "746 records" as a small-n study. That framing is
fair.

## 5. Two citations are UNVERIFIED — **DECISION**

`scripts/check_paper_refs.py` passes, but flags:

- `elyaniv` — El-Yaniv & Wiener, *On the foundations of noise-free selective
  classification*, JMLR 2010
- `geifman` — Geifman & El-Yaniv, *Selective classification for deep neural
  networks*, NeurIPS 2017

Both are real papers. Neither registers a DOI with Crossref, so I could not
machine-verify volume, pages, or the exact author list, and I refused to
invent them. They carry `UNVERIFIED` notes in `paper/references.bib`.

**Needed:** someone confirms both by hand at jmlr.org and
proceedings.neurips.cc, then deletes the note lines. Fifteen minutes.

The other three (txgnn, chow, rubin) are Crossref-verified against live DOIs.

## 6. Double-blind hazard: your prior work — **DECISION**

The submission is double-blind. `scripts/check_anonymity.py --strict` passes
on `paper/` and blocks the obvious terms, including `zenodo`.

The problem: the FCO/FCG custody framework is yours and is published under
your name. Citing it correctly identifies you as an author. Not citing it
leaves the paper's central architectural idea uncredited, which is worse.

Three options, and I do not think this is mine to pick:

1. **Cite it in third person** ("the fractal custody construction of [X]") and
   accept the deanonymisation risk. Common and usually tolerated, but a
   determined reviewer connects it.
2. **Describe the mechanism without citing** for the review copy, and add the
   citation in the camera-ready. Standard practice, and the anonymity checker
   currently enforces this by default.
3. **Cite anonymously** ("[anonymised prior work]"), which OpenReview supports.

The draft currently does (2) by omission. Tell me which you want.

## 7. The NeurIPS style file is not installed — page count is approximate

`neurips_2026.sty` is not in the repo. `main.tex` detects this and falls back
to a geometry+natbib approximation of the single-column layout, so the draft
compiles and reads correctly, but **the 7-page count is not authoritative**.

Drop the official `.sty` from the Overleaf template next to `main.tex` and it
is picked up with no edits. Expect the real layout to be tighter than what you
are reading. The workshop limit is 2–8 pages excluding references, and we have
headroom either way.

Keep the anonymous default. Do **not** add `[final]` until acceptance.

## 8. Nothing in this system folds a protein

Worth stating plainly because the FASTA output invites the assumption: there
is **no AlphaFold, ESMFold, or ColabFold call anywhere in the codebase**. The
only mentions are in two internal docs describing it as a possible future
HealthOmics Ready2Run step.

The sequence lane emits FASTA. The paper's claim is that 16 of those files
*would have been* silently wrong and that a structure predictor would have
accepted them without complaint. That claim is about what a downstream tool
would do with the input, and we did not run one.

If you want the stronger version — actually folding a wrong sequence and
showing the confident garbage structure — that is a real experiment we have
not done, and I would not try to land it before the 29th.

## 9. We do not evaluate whether any of this is biologically true

The claim ceiling is enforced in code: `REPURPOSING_HYPOTHESIS` is the highest
verdict the system can emit, and no path reaches a therapeutic claim.
Establishing that any proposed pairing is correct needs wet-lab work.

This is the right ceiling, and it also means the paper has no biological
result. It is a systems and evaluation paper that happens to run on
biomedical data. If NewInML reviewers expect a biology contribution, that is a
scope mismatch we should anticipate.

## 10. Fourteen commits carry an AI co-author trailer — **DECISION**

14 of 31 commits on `healthomics-lane` have a `Co-Authored-By: Claude` trailer
from before the no-watermark rule was set. Everything since is clean.

Stripping them means `git filter-branch`/`filter-repo` and a force-push, which
rewrites every SHA on the branch. Options:

1. **Leave them.** They are on my fork, not `biobitworks/protein-hinge`, and
   the anonymised artifact for reviewers is a code drop rather than a git
   history.
2. **Rewrite and force-push** before anyone else branches from it.

I lean toward (1) — the rewrite risk is real and the exposure is low — but
if the artifact ends up being the repo itself, it becomes (2), and it should
happen before you pull.

---

## What is verified and needs nothing from you

- All numbers in the PDF are generated from pipeline output by
  `scripts/build_paper_tex.py`. No figure is typed by hand.
- `check_cited_numbers.py` — clean. No superseded figure survives in any of 12
  documents (13 retired values tracked).
- `check_anonymity.py --strict` — clean on all 4 submission files.
- `check_paper_refs.py` — clean; all 6 citations present in the bib, no
  undefined macros.
- LaTeX compiles with no errors and no undefined references or citations.
- Acquisition reconciles: 746 fetched = 364 admitted + 382 excluded + 0
  unavailable.
- Sequence lane reconciles: 364 in = 98 emitted + 266 declined.
- All 98 emitted sequences verified position-by-position against wild-type.

## Current headline numbers

| Guard | Silent errors prevented | Rate |
|---|---|---|
| G1 residue verification | 16 / 114 emitted | 14.0% |
| G2 copy-number exclusion | 382 / 746 records | 51.2% |

G2 moves 3 of 8 genes (PGS1, PHB2, CHCHD3) from apparent support to zero.

Note that G1 was **24.6%** in the draft before last. That figure was wrong: the
pipeline tested the residue precondition before classifying the variant, so
frameshifts that also mismatched were counted as residue mismatches. The
emitted sequences were byte-identical before and after the fix — only the
reasons were wrong. It was a measurement defect, and it is disclosed in
Section 5 of the paper rather than quietly corrected.
