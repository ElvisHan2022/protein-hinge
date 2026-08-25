# Methods + Evaluation — outline for review

Read §0 first. It answers "what are we evaluating and why," which is the part
that has been unclear. Nothing here is prose yet — this is the skeleton to
approve or redirect before I write.

---

## 0. What we are evaluating, and why

### The trap

The instinct is: *we built a drug–disease matcher, so evaluate the matches.*
**We cannot.** Deciding whether a proposed repurposing candidate is *correct*
requires wet-lab validation we have not done. Any paper claiming otherwise
would be unpublishable and wrong. This is why the evaluation felt undefined —
the obvious metric is unavailable.

### The reframe

The novel thing in this system is not the matching. It is that **the system is
built to refuse.** Every stage must either verify its input or decline it, and
declining is a first-class, counted output rather than an empty result.

So we do not evaluate the matches. **We evaluate the refusals** — by asking
what happens when you remove them.

> **The experiment is an ablation: enforcement ON vs. enforcement OFF, over the
> same real inputs.** We already have ON. Turning each guard OFF simulates the
> ordinary pipeline anyone would write, and we count what it would have emitted.

### The metric: silent error rate

A **silent error** is an output that is (a) wrong, (b) syntactically
well-formed, (c) raises no exception or warning, and (d) is indistinguishable
to a downstream consumer from a correct output. It is the non-statistical
analogue of a hallucination: plausible, confident, undetectable at the point of
use.

$$\text{silent error rate} = \frac{\text{wrong outputs a naive pipeline emits}}{\text{total outputs a naive pipeline emits}}$$

We report it per guard, with the absolute counts, over real public data.

### Why an ML venue should care

Provenance and abstention are usually argued for on principle. This paper
argues for them with a number, in a setting where the failure is *silent* — the
same reason hallucination is hard. And the intervention is architectural
(verify-or-abstain, enforced in code) rather than statistical, which makes it
transferable to any evidence-assembling pipeline, LLM-driven or not.

### The three guards we measure

| Guard | What it verifies | Why failure is *silent* |
|---|---|---|
| **G1 — residue verification** (sequence lane) | the wild-type residue a variant record names matches the canonical sequence at that position | The emitted FASTA is valid, the residues are real, a folding tool accepts it without complaint. The structure is simply of a protein nobody has. |
| **G2 — copy-number exclusion** (genetics lane) | a variant record is gene-specific, not a multi-gene chromosomal event | The count is just a number. It ranks genes, and it looks identical whether or not it is attributing a whole-arm deletion to one gene. |
| **G3 — closed-vocabulary resolution** (identity layer) | a symbol resolves by exact match or an explicit alias, never by similarity | `TAZ` resolves to two unrelated proteins (tafazzin; WWTR1). A fuzzy match returns a real gene, and every downstream step succeeds — about the wrong protein. |

### The measurements (verified, from the repo)

**G1 — residue verification.** Of 364 records, 246 carry protein-level
notation; 131 of those are frameshifts that cannot be reconstructed from the
record at all, leaving **115 substitution-eligible**. A naive pipeline emits
**114** of them (1 fails on array bounds — a *loud* error, not a silent one).
**16 of those 114 are silently wrong** — the named wild-type residue does not
match the canonical sequence, i.e. the record is numbered against a different
isoform.

> **Silent error rate without G1: 16/114 = 14.0%.**

**G2 — copy-number exclusion.** Of 746 fetched ClinVar records, **382 are
multi-gene copy-number events** (51.2%). The per-gene effect is not uniform,
which is the interesting part:

| Gene | naive count | after G2 | what the naive count was actually counting |
|---|---|---|---|
| PHB2 | 46 | **0** | Chromosome 4q21 deletion syndrome |
| CHCHD3 | 32 | **0** | Ring chromosome 7 |  <!-- numbers-ok: gene count -->
| PGS1 | 14 | **0** | whole-region events |
| CRLS1 | 33 | 3 | mostly regional |
| TAFAZZIN | 339 | 109 | |
| HADHA | 267 | 251 | |

Three of eight genes go from apparent evidence to **honest zero**. A naive
pipeline reports them as supported.

**G3 — closed-vocabulary resolution.** Demonstrated, not counted (n=1 in this
corpus): `TAZ` is marked `UNRESOLVED` and abstains rather than fuzzy-matching.
Report as a worked example, **not** as a rate — we do not have the sample size.

### Custody: a property, not a result

Single-byte tamper detection follows by construction from a Merkle tree. We
**demonstrate** it (the verification re-runs client-side and names the first
divergent node) and report the cost, but we do **not** dress it up as an
experimental finding. Overclaiming here is the fastest way to lose a reviewer.

### What we explicitly do not evaluate

- whether any proposed pairing is biologically correct — needs wet-lab work
- generalisation beyond the validation disease — the decision layer currently
  runs end-to-end on one prescripted case
- efficacy, treatment value, or clinical utility of anything

---

## Resolved while verifying these numbers

**The genetics lane was silently dropping records, and fixing it changed the
corpus.** 746 record ids were fetched but only 642 accounted for <!-- numbers-ok: historical -->; exactly one
100-record batch vanished through a bare `continue` with nothing recorded.

Diagnosis went wrong once before it went right, which is worth reporting in the
paper. The batch failed every retry, but tested alone it succeeded, so the first
conclusion was throttling. Testing *every* batch rather than the first one
showed a specific batch failing reproducibly with a real message: the source
refuses to convert a response over 10 MB to JSON, and a single copy-number
record listing over a thousand genes pushed the batch past that limit. Our own
error handler read three possible error keys and the source uses a fourth — so
the guard noticed the loss but discarded the explanation.

**Now:** a failing batch is split and retried until the oversized record is
isolated, so its neighbours survive. Every fetched id lands in exactly one
bucket and the run asserts the balance. Result: **746 fetched = 364 kept + 382
excluded + 0 unavailable**, and the 100 records came back — 9 gene-specific,
91 copy-number.

Two consequences for the paper:
1. **The numbers above are the post-fix ones.** The pre-fix corpus was
   incomplete, and every earlier figure was quietly wrong.
2. **The oversized records are the copy-number records** — the same class G2
   exists to exclude. The size failure and the misattribution have one cause.

## Methods — section outline

**3.1 Task and outputs.** Input: a rare disease. Output: a set of
(disease, target, drug-program) rows, each with a verdict in
{GAP, NOT_A_GAP, ABSTAIN}, the rule that produced it, and a receipt. Define
what a receipt is. State the claim ceiling as a design constraint, not a hedge.

**3.2 Evidence acquisition.** The five sources, one question each. The
capture-time discipline: every response hashed at origin, query URL recorded,
distinction between *recomputed* (we hold the bytes) and *committed* (we hold a
digest from origin). Why an unre-queryable source is inadmissible — and that
this rule is what keeps one source dashed rather than quietly included.

**3.3 Identity normalisation.** The closed alias table; exact / mapped /
unresolved; no fuzzy matching anywhere. This is the layer where silent errors
are born, so it gets its own subsection. → **guard G3**

**3.4 Decision procedure.** G000–G008, first-match-wins, plain Python,
self-tested. Explicit statement that no model output can set a verdict, resolve
a symbol, or choose a threshold — an architectural constraint, not a policy.
The abstention states and what each means.

**3.5 Verification guards.** The formal statement of verify-or-abstain, and the
three instantiations (G1, G2, G3) with their preconditions. **This is the
subsection the evaluation depends on** — the rest of Methods exists to make
this one legible.

**3.6 Custody.** Content-addressing, RFC 6962 over all lanes, one root,
client-side re-verification, tamper behaviour. Kept short and factual.

**3.7 Implementation and reproducibility.** Every number regenerable from the
repo by a single script; anonymised artifact; corpus date pinning so the graph
is stable across runs.

---

## Evaluation — section outline

**4.1 Setup.** The ablation: enforcement ON (the system) vs. OFF (the pipeline
a competent engineer writes without these guards). Same inputs, same sources,
same corpus snapshot.

**4.2 Metric.** Silent error rate, defined as above. Justify why *silent* is
the right qualifier and why loud failures are excluded from the numerator.

**4.3 Results.** The table (G1 24.6%; G2 51.2% of records, three genes from
apparent evidence to zero; G3 as a worked example). Absolute counts always
shown beside rates — the denominators are small and hiding that would be
dishonest.

**4.4 Cost.** What enforcement costs: 266 of 364 records declined in the
sequence lane. State plainly that the system's answer is "I don't know" far more
often than not, and argue that this is the correct behaviour for the setting.

**4.5 Threats to validity.** One corpus, one disease family, small
denominators, guards designed by us and evaluated by us on data we selected.
Say all of it.

---

## What I need from you

1. **Does §0 match your understanding of what we built?** If the reframe (we
   evaluate the refusals, not the matches) doesn't sit right, that's the thing
   to argue about now — everything else follows from it.
2. **Green light to fix the 100-record accounting gap** before I write prose.
3. Anything in the Methods outline that misstates the biology.
