# Elvis — scope and to-do

**Deadline: Aug 29.** Written 16:00, Aug 24.

---

## Your scope, in one line

**Byron owns the science and the narrative. You own the system and the
evidence.** He brings the biology, the paper draft, the FCO/FCG design, and the
lab. You bring the thing that runs, the numbers it produces, and the proof those
numbers are checkable.

For the paper specifically, that makes you the author of:

- the **Method** section — the architecture (GATHER / GRADE / PROVE, G000–G008, custody)
- the **Results** section — the measured errors-prevented table
- the **figures** — workflow DAG + results table
- the **anonymisation pass** — the thing that keeps us from a desk reject

Byron owns title, abstract, intro, related work, and the biology framing.

---

## To-do

### Today (Aug 24) — 3 items, ~20 minutes of your time

- [ ] **Ask Byron for his paper draft.** One message. Blocks the most work of
      anything on this list. Also ask: does the "no prior top-ML publication"
      eligibility rule bind *all* authors or just one?
- [ ] **Create your OpenReview account.** Activation can lag; do not leave this
      to the 28th.
- [ ] **Open the PR** → `biobitworks/protein-hinge`, branch `healthomics-lane`.
      Nothing gets reviewed until this exists.

### This week (Aug 25–28)

- [ ] Answer the one decision that shapes the week: **paper-first or
      platform-first** (see below — my recommendation is paper-first)
- [ ] Review the Method + Results sections I draft, for scientific accuracy —
      you know the biology framing better than I do
- [ ] Refresh AWS credentials **if** we need a live probe for a figure (the
      event credentials are temporary and expire)
- [ ] Send Byron your ORCID, preferred email, LinkedIn, and bio blurb (his ask —
      I can draft the blurb if you tell me what to emphasise)
- [ ] Final anonymity read-through before submit — two pairs of eyes
- [ ] **Submit Aug 28**, not the 29th. Portals get slow at deadlines.

### After Aug 29 (post-submission, before Sep 29 notification)

- [ ] Live disease → target resolution — the missing link for end-to-end
- [ ] ChEMBL as the admissible replacement for the dashed Convoke box
- [ ] Wire the rules to live inputs, keep the Barth fixture as a regression test
- [ ] Conversation custody (FCO/FCG) — needs Byron's design notes
- [ ] In vitro protocol drafts + FDA readiness matrix — Byron's remaining two of three

---

## What I need from you right now

Ranked. Only the first genuinely blocks me.

| # | Need | Why | Cost to you |
|---|---|---|---|
| **1** | **Go/no-go on paper-first** | Decides what I build tomorrow. Absent a different answer I proceed as below. | one word |
| 2 | Byron's draft (via your ask) | Stops me duplicating sections he already wrote | one message |
| 3 | Scientific review of what I draft | I can write it; I should not be the last check on the biology | ~30 min later this week |

**Not blocking me, but blocking *you*:** OpenReview account, the PR, ORCID/bio.

---

## What I'm starting on unless told otherwise

1. `scripts/build_paper_metrics.py` — regenerates the results table from the
   repo so every number in the paper is reproducible and receipted. This is
   certainly not in Byron's draft; it's our data.
2. The **Results** section prose around that table.
3. The **Method** section, compressed from the README and deck to ~1.5 pages.

All three are useful whichever way the paper-vs-platform call lands, and none
of them need anything from you to begin.

---

## The recommendation, restated

**Freeze the platform. Write the paper.** The measurements for a defensible
2–8 page workshop paper already exist. The platform work (live disease→target,
ChEMBL, wiring the rules) is better done after Sep 29 notification, where it
strengthens the camera-ready and the poster instead of competing with a
five-day deadline.
