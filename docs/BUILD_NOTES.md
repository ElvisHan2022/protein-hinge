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

**Did:** filter out multi-gene copy-number events. 746 → 364 records. PHB2,
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

**Noticed:** when rebuilding protein sequences from variant records, 16 of them
named a starting amino acid that did not match the real sequence at that spot.

**Why it matters:** this is the sharpest example we have. If you skip the check,
you produce a FASTA file that is perfectly valid, full of real amino acids, that
any folding tool will happily accept — and the answer is about a protein nobody
has. Nothing errors. Nothing warns.

**Did:** only apply a substitution when the named residue matches. 16 refused,
98 emitted and all 98 verified correct.

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

### 9. I misdiagnosed it, and the error message was hiding

**First guess (wrong):** the batch retried four times and still came back empty,
but tested on its own it returned all 100 records fine — so I concluded my own
repeated re-runs had throttled the source, and widened the retry waits.

**What it actually was:** testing every batch individually, not just the first
one, showed a specific batch failing every time with a real message:

> `Input XML size is 16503275 bytes, and cannot be transformed to JSON. the max size is 10MB`

Some ClinVar records are enormous — a single copy-number entry can list over a
thousand genes — and one of them pushed its batch past the source's 10 MB
conversion limit. Structural and completely reproducible, not load at all.

**Why I could not see it:** the source returns that message under a different
key than the ones my error handler read, so my own log said only "response
carried no result payload." **I had built a guard that noticed the loss but
discarded the reason.**

**Did:** read the real error key, and split a failing batch in half and retry
until the oversized record is isolated on its own. Its neighbours are recovered
instead of dying with it.

**For the paper, two lessons:**
1. *Detecting* a loss and *explaining* it are different jobs. We had the first
   and thought we had the second.
2. My first diagnosis was confidently wrong and would have shipped — the thing
   that corrected it was testing every case rather than the first one that
   looked representative.

---

### 10. Live data moves under us

**Noticed:** between two runs an hour apart, ClinVar went from 742 to 746
records for the same query.

**Why it matters:** any number in the paper is a snapshot. Two honest runs
disagree slightly, and a reviewer re-running it next month will get a third
answer.

**Did:** flagged it. The paper must pin a corpus date and report the digest of
the exact table the numbers came from — which the pipeline already records.


---

### 11. The oversized records are the ones we were already excluding

**Noticed:** the batch that broke the size limit is full of copy-number records
— the same multi-gene events the filter in note 1 throws out.

**Why it matters:** two problems with one cause. Those records are enormous
precisely *because* they span hundreds or thousands of genes, which is also
exactly why they are not evidence about any single gene. The size crash was a
symptom of the same thing the filter exists to remove.

**Did:** nothing extra — but it is a satisfying consistency check, and worth a
sentence in the paper.


---

### 12. The audit found a bug in my own headline number

**Noticed:** running the six audit questions, an independent recount of the
mismatches gave 17; the pipeline reported 32.

**Why it matters:** the pipeline checked "does the residue match?" *before*
"is this a frameshift?". Frameshifts cannot be rebuilt at all, so a frameshift
that also mismatched was filed under *mismatch*. That inflated the headline
figure with 16 records **no substituting pipeline could ever emit**.

The reported silent-error rate was **24.6%**. The true rate is **14.0%** —
overstated by more than ten points, in the direction that flattered us. The
sequences we emit never changed: the guard rejected exactly the same records.
Only the reasons were wrong. **A measurement bug, not a behaviour bug** — which
is precisely why nothing looked broken.

**Did:** classify the variant before checking the residue. 16/114 = 14.0%.

---

### 13. The rejected records are not garbage — they are correctly numbered against a different transcript

**Noticed:** the guard rejects because "the residue does not match", but I had
never checked *why*. That is asserting a cause, not measuring one.

**Why it matters:** testing the failing records (rather than the passing ones)
showed a single constant offset of **+30 reconciles all 16 exactly**. ClinVar
numbers these against the longer TAFAZZIN transcript; UniProt canonical is 30
residues shorter.

So the records are valid — in their own frame. Applied to the canonical
sequence they are silently wrong, so the error is real. But they are
**recoverable**, and right now we throw them away. Abstention is the safe
answer, not the best one.

---

### 14. The whole effect comes from one gene

**Noticed:** all 16 mismatches are TAFAZZIN. HADHA contributes 69 emitted
sequences and **zero** mismatches; CRLS1 and PTPMT1 zero.

**Why it matters:** the measured G1 result is not "eight genes show this" — it
is one gene with one transcript-numbering convention. n = 1, not 8. A reviewer
will find this in a minute, so we state it in Limitations ourselves.

**Did:** nothing to the code. It goes in the paper as a threat to validity.

---

### 15. The same silent-drop shape was still in my own code

**Noticed:** auditing every error path found `if not rec: continue` in the
sequence lane — a record whose gene failed to resolve would vanish uncounted.

**Why it matters:** identical in shape to the bug that lost 100 records. It had
not fired only because all eight genes happen to resolve. Latent, not absent.

**Did:** counted as `gene_unresolved`, and the sequence lane now asserts its own
balance: 364 in = 364 accounted.
