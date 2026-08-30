# Submission guide — NewInML @ NeurIPS 2026

Consolidates four sources: Byron's Discord messages (8/17), the NewInML call
for papers, Yassa's `SUBMIT-NOW.md` (8/29), and the verification run in this
repo on 8/29–8/30. Where they disagree, the disagreement is named rather than
smoothed over.

**Deadline: Aug 29 2026, 11:59pm AoE = 04:59 Pacific, Sat Aug 30.**
AoE is a hard cutoff. OpenReview slows in the final hour.

---

## 1. What is submitted

One PDF. Nothing else is required.

| | |
|---|---|
| Format | A written **paper**. Not a poster, not an abstract. |
| Length | **2–8 pages excluding references**, NeurIPS 2026 workshop template |
| Review | **Double-blind**, full anonymisation |
| Platform | OpenReview |
| Eligibility | Open to anyone who has **not** published at a top ML conference (NeurIPS, ICML, ICLR, …) |

The poster is built in Nov–Dec **only if accepted** (notification Sep 29,
camera-ready Nov 29, workshop Dec 11). Code and artifacts are optional
supporting material for this workshop; the repo is not itself a submission.

**Eligibility is resolved.** Byron on Discord, 8/17: *"For eligibility, I have
never published to another top ML conference before, so this will be my first
time."* Elvis likewise. The open question in the old checklist about whether
the rule binds all authors or one is moot if it holds for everyone — confirm
the same for any additional author before adding them.

---

## 2. Which PDF

**Two different files are in circulation for one submission.** Resolve this
before anyone uploads.

| | `SUBMIT-NOW.md` names | This repo builds |
|---|---|---|
| Path | `/Users/yassa/Desktop/paper-rebuild/main.pdf` | `paper/main.pdf` |
| Size | 114,874 bytes | 320,660 bytes |
| MD5 | `2dd5bf9938205afa49e02b19b48da51f` | current build, rehash before upload |
| Exists on Elvis's machine | no | yes |

`Downloads/main.pdf` on Elvis's machine is the repo build, not the rebuild.

**Recommendation: submit the repo build.** Three reasons.

1. **Its numbers have an intact provenance chain.** `SUBMIT-NOW.md` states that
   the rebuild's `generated/results.tex` was reconstructed by reading figures
   out of a PDF. That is not true of this repo: copying the committed file,
   re-running `scripts/build_paper_tex.py`, and diffing gives a byte-identical
   result. The Reproducibility statement holds here without qualification, and
   for a paper whose thesis is verifiability that distinction is the whole
   argument.
2. **Two defects were fixed after the rebuild was cut** (§3). If the rebuild
   came from the same `.tex` and `.bib`, it carries both.
3. **It is verifiably anonymous** (§5), so the "do not recompile" rule that
   `SUBMIT-NOW.md` imposes is unnecessary here.

`SUBMIT-NOW.md` is right that recompiling *can* stamp a system username into
`/Author`. It does not on this machine — checked, not assumed. Rehash and
re-scan after any rebuild rather than trusting this note.

---

## 3. Two defects fixed on 8/30 — do not ship a build from before this

Both were visible in the rendered PDF, neither raised an error. Commit
`d0e992b`.

1. **A date on the title page.** `\maketitle` was stamping "August 28, 2026"
   onto a double-blind submission. Fixed with `\date{}`.
2. **Internal notes typeset into the bibliography.** The `UNVERIFIED` working
   notes on two references sat in bibtex `note` fields, so `plainnat` rendered
   them. A reviewer would have read *"UNVERIFIED — confirm at
   proceedings.neurips.cc before submission"* in the References section. Moved
   to comments after each entry, which keeps `check_paper_refs.py` flagging
   them while bibtex ignores them.

`SUBMIT-NOW.md`'s own checklist says page 1 should carry "no real names, no
date" and then does not check for the date. Check it.

---

## 4. Formatting — the one real gap

**Template (from Byron, Discord 8/17):**
<https://www.overleaf.com/latex/templates/formatting-instructions-for-neurips-2026/bjdwqfdkyftc>

**`neurips_2026.sty` is not in this repo.** `paper/main.tex` detects its
absence and falls back to a geometry + natbib approximation, so the paper
compiles and reads correctly, but **the page count is not authoritative**.

```
\IfFileExists{neurips_2026.sty}{\usepackage{neurips_2026}}{...fallback...}
```

To fix: download the template from the link above, drop `neurips_2026.sty`
beside `main.tex`, recompile. No edits needed — it is picked up automatically.

**Keep the anonymous default. Do not add `[final]`** until acceptance; that
option prints author names.

**Page budget.** The fallback build is 7 pages: 6 body + 1 references. The
limit is 8 excluding references, so there is roughly two pages of headroom.
The real style has a narrower, taller text block, so the true count should land
at or below 6 body pages. Low risk, still unverified — confirm after dropping
the `.sty` in.

---

## 5. Anonymity — verified, not assumed

Run on `paper/main.pdf`, 8/30:

- `/Author`, `/Title`, `/Subject`, `/Keywords` — **all empty**
- `/Creator` `LaTeX with hyperref`, `/Producer` `pdfTeX-1.40.29` — generic
- Raw-byte scan for 17 identity strings (names, emails, `biobitworks`,
  `protein-hinge`, `Users/`, `C:\Users`, tooling names) — **zero hits**
- Page 1 reads `Anonymous Author(s) / Affiliation withheld for review`, no date
- `scripts/check_anonymity.py --strict` — clean across all 4 submission files

Anonymity in the PDF is separate from the authors field in the OpenReview form.
The PDF is anonymous; the form takes real names. OpenReview handles the
blinding.

---

## 6. The OpenReview form

| Field | Value |
|---|---|
| Title | Enforced Abstention Prevents Silent Errors in Biomedical Evidence Pipelines |
| Authors | **Every author, including whoever submits.** See below. |
| Abstract | Copy from page 1 of the PDF |
| PDF | `paper/main.pdf` (this repo) |
| Keywords | selective prediction, abstention, provenance, drug repurposing |
| Supplementary | Skip — the paper promises no artifact link once §7.3 is settled |

**The authors field is what actually credits people.** Each author needs an
openreview.net account with a completed profile (name, email, affiliation) —
Byron's step 1 from Discord. OpenReview blocks submission on incomplete
profiles, and an email that does not match a profile creates a second identity
whose authorship does not attach. Get the full list from Byron before starting,
rather than guessing at 4am.

Byron also asked (Discord, 8/17) for each person's **ORCID, preferred email,
LinkedIn, and bio blurb**. That was for the hackathon portion, not the
OpenReview form, but the email should be the same one as the profile.

---

## 7. Open decisions — all three affect the PDF

### 7.1 Citing Byron's prior custody work
The FCO/FCG framework is his and is published under his name. Citing it
identifies him; omitting it leaves the paper's central architectural idea
uncredited. Options: cite in third person and accept the risk; describe the
mechanism without citing for review and add it camera-ready; or cite as
`[anonymised prior work]`, which OpenReview supports. **The draft currently
omits by default.**

### 7.2 Two UNVERIFIED citations
`elyaniv` (JMLR 2010) and `geifman` (NeurIPS 2017). Both are real papers;
neither registers a DOI with Crossref, so volume and pages were never
machine-verified and were not invented. Now cosmetic, since the notes no longer
print. ~15 minutes at jmlr.org and proceedings.neurips.cc.

### 7.3 The Reproducibility statement
Currently: *"...is available to reviewers [link withheld for anonymous
review]"* — an unfilled placeholder promising a link that does not exist, in a
paper arguing for verifiability. Yassa's proposed replacement: *"...will be
released publicly on publication."* Weaker but keepable. The strong version
needs a real `anonymous.4open.science` mirror standing up before the deadline.
**Recommendation: take the weaker sentence given the clock.**

---

## 8. Pre-flight

Run from the repo root. Everything below passed on 8/30 except where noted.

```bash
py scripts/build_paper_metrics.py && py scripts/build_paper_tex.py && py scripts/check_cited_numbers.py && py scripts/check_anonymity.py --strict && py scripts/check_paper_refs.py
```

- [ ] `neurips_2026.sty` dropped in and recompiled (§4) — **outstanding**
- [ ] Page count ≤ 8 excluding references, confirmed under the real style
- [ ] §7.1, §7.2, §7.3 decided and the PDF rebuilt
- [ ] Page 1: `Anonymous Author(s)`, no real names, **no date**
- [ ] No `UNVERIFIED` string anywhere in the rendered PDF
- [ ] PDF metadata re-scanned after the final rebuild
- [ ] Author list complete, every email matching an OpenReview profile
- [ ] Submitted, and the submission number posted to Discord

OpenReview allows edits until the cutoff. Submitting early costs nothing.

---

## 9. Where each claim came from

| Source | Date | Carries |
|---|---|---|
| Byron, Discord | 8/17 | Overleaf template link, OpenReview accounts, his eligibility, ORCID/email/LinkedIn/bio request |
| NewInML CFP | fetched 8/24 | page limits, double-blind, deadlines, eligibility rule, poster-if-accepted |
| `SUBMIT-NOW.md` (Yassa) | 8/29 | AoE deadline math, `/Author` recompile hazard, authors-field guidance, the Reproducibility critique |
| This repo, verified | 8/29–8/30 | PDF metadata scan, `results.tex` regeneration diff, the two defects in §3, guard results |

Claims in `SUBMIT-NOW.md` that did **not** hold against this repo: that the
checked-in `results.tex` is a hand-reconstruction, and that the file to upload
is the 114KB rebuild. Both are noted in §2 rather than deleted, because they
may be accurate about the tree Yassa was working in.
