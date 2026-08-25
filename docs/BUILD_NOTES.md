# Build notes — things that caught my attention, and why

Running log, newest last. Plain language on purpose: each entry says what I
noticed, why it mattered, and what I did. Several of these are candidate
material for the paper, because the pipeline keeps producing examples of the
exact failure the paper is about.

---

### 1. The counts were measuring the wrong thing

**Noticed:** PHB2 showed 46 "pathogenic variant" records, and its top reported
condition was *Chromosome 4q21 deletion syndrome*.

**Why it matters:** that is not evidence about PHB2. It is a deletion spanning a
whole chunk of a chromosome that happens to include PHB2 — like blaming one
house for a city-wide blackout. Three of our eight genes were scoring entirely
on events like this.

**Did:** filter out multi-gene copy-number events. 642 → 355 records. PHB2,
CHCHD3 and PGS1 fell to an honest **zero**.

---

### 2. A gene name that means two different proteins

**Noticed:** the demo showed the target as "TAZ", and our own alias table marks
`TAZ` as UNRESOLVED.

**Why it matters:** "TAZ" is used for both tafazzin (the Barth gene) and WWTR1,
a completely unrelated protein. Anything downstream would still work — it would
just be about the wrong protein, with no error anywhere.

**Did:** display **TAFAZZIN (TAZ)**, and kept the alias table refusing to guess.

---

### 3. Variant records numbered against a different protein

**Noticed:** when rebuilding protein sequences from variant records, 28 of them
named a starting amino acid that did not match the real sequence at that spot.

**Why it matters:** this is the sharpest example we have. If you skip the check,
you produce a FASTA file that is perfectly valid, full of real amino acids, that
any folding tool will happily accept — and the answer is about a protein nobody
has. Nothing errors. Nothing warns.

**Did:** only apply a substitution when the named residue matches. 28 refused,
95 emitted and all 95 verified correct.

---

### 4. One slow cloud call froze the entire dashboard

**Noticed:** the new tab rendered blank, and the whole page hung.

**Why it matters:** the demo server handled one request at a time. An AWS call
with expired credentials retried for tens of seconds, and everything queued
behind it — including the page's own data files. On stage this looks like the
project is broken.

**Did:** made the server threaded. Confirmed pages load while a slow call is
still in flight.

---

### 5. Our own integrity test could not run on this machine

**Noticed:** `node site/verify_test.js` threw immediately.

**Why it matters:** that test is the project's definition of done — it re-checks
the whole evidence chain. It reads the dashboard source looking for markers
written with Unix line endings, but git hands out Windows line endings on this
machine, so it never found them. It had been failing before I touched anything.

**Did:** normalise line endings first. It now passes: the root matches, and
tampering still moves it.

---

### 6. The docs described an outcome the cloud account forbids

**Noticed:** README, deck, script and diagram all said the genetic data was
"loaded into an AWS HealthOmics annotation store."

**Why it matters:** the hackathon account blocks that API outright. We were
describing something that cannot happen there — the exact kind of unearned claim
this project exists to prevent.

**Did:** corrected every mention to what actually runs (upload to S3 plus a VEP
workflow run), and marked the superseded script as such.

---

### 7. The account number was sitting in committed files

**Noticed:** the AWS account id appeared in four receipt files and a screenshot.

**Why it matters:** the project's own rules say receipts mask everything, and
they did not. It is also an identity leak, and the paper submission is
anonymous.

**Did:** redacted it from the files and from the code that writes them.

---

### 8. We were silently losing 100 records — the same failure we indict

**Noticed:** the genetics lane fetched 742 record ids but only accounted for 642
downstream. Exactly one batch of 100 vanished.

**Why it matters:** this is the paper's thesis landing on our own code. A single
`continue` with nothing recorded, and 13% of the evidence disappeared without a
trace. Every per-gene number would have looked entirely normal.

**Did:** every fetched id must now land in exactly one bucket (kept, excluded,
or unavailable), and the run prints BALANCED or UNBALANCED. Unavailable records
are a counted abstention with a stated reason.

---

### 9. …and the cause was us, not them

**Noticed:** the failing batch retried four times and still came back empty —
but tested on its own, with breathing room, it returned all 100 records fine.

**Why it matters:** the data source throttles sustained bursts and answers a
throttled request with a normal-looking, empty reply. My repeated full re-runs
caused it, and my retry waits (1.5–6 seconds) were too short to outlast the
throttle. So the pipeline's own data collection is **non-deterministic under
load** — and without the reconciliation check from note 8, we would never have
known which run was complete.

**Did:** widened the backoff to 2/5/15/30 seconds and slowed the batch cadence.

**For the paper:** this is the strongest self-referential example we have. The
governance did not just catch bad upstream data — it caught *us*, twice, in a
week.

---

### 10. Live data moves under us

**Noticed:** between two runs an hour apart, ClinVar went from 742 to 746
records for the same query.

**Why it matters:** any number in the paper is a snapshot. Two honest runs
disagree slightly, and a reviewer re-running it next month will get a third
answer.

**Did:** flagged it. The paper must pin a corpus date and report the digest of
the exact table the numbers came from — which the pipeline already records.
