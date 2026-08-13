# Protein Hinge: Plain-Language Brief

## The Thought Process, Start to Finish

**The pain point we address:** over 90% of rare diseases have no approved
treatment, while existing drugs that might help sit untried — and when AI
tools do propose a match, nobody can check their work, so trials get
duplicated and leads get ignored.

**What people in the field are doing:** machine-learning platforms (TxGNN,
Every Cure's MATRIX, Healx) score millions of drug–disease pairs, and
subscription databases sell the landscape. Powerful rankings; black boxes.

**What we do:** grade drug–disease pairings with simple readable rules over
five public evidence sources, and fingerprint every piece of evidence so the
answer can be verified by anyone, on their own machine. The AI presents; it
never decides.

**Our workflow is broken into a GATHER, a GRADE, and a PROVE phase.**
The input is a rare disease name. The output is a graded table of existing
drugs with a verifiable receipt on every row.

- **GATHER:** ask five public sources one question each — Open Targets (what
  biology is broken?), ClinVar loaded toward an AWS HealthOmics annotation
  store (do patients carry pathogenic variants in these genes?),
  ClinicalTrials.gov (has this pairing been tried?), openFDA (is the drug
  approved?), JUMP Cell Painting (does any compound push sick-looking cells
  back toward healthy?). Every response is hashed the moment it arrives.
  *Tech: Python, public REST/GraphQL APIs, boto3 + S3 + IAM + HealthOmics.*
- **GRADE:** nine plain-Python rules decide GAP, NOT_A_GAP, or ABSTAIN for
  each pairing. "We cannot say" is shown as loudly as any result. No machine
  learning makes any decision. *Tech: plain Python.*
- **PROVE:** every record is content-addressed under one Merkle root, and the
  dashboard re-verifies the whole chain inside the reader's browser — with a
  live demonstration that changing one byte of evidence gets caught.
  *Tech: SHA-256 / RFC 6962, SQLite, sql.js in WebAssembly.*

AWS status, honestly: the ClinVar subset and the HealthOmics store pipeline
are built; no data has been generated in AWS yet, and the dashboard abstains
in writing until it has.

## One-Sentence Version

Protein Hinge shows a disease-first repurposing idea, the cell-perturbation
evidence behind it, and a custody trail that lets another person check what was
used and whether anything was changed.

## What The Demo Shows

1. Start with a rare disease question.
2. Show whether a known program already exists for that disease.
3. Show a real cell-perturbation figure from processed public Cell Painting
   data.
4. Show the evidence records behind the claim.
5. Rebuild the hash root in the browser.
6. Tamper with one record and watch the verification fail.

## The Disease Search Component

The Disease Search view turns the demo into a rare-disease repurposing finder.
The internal teammate handoff was labelled "Elvis"; users do not need that
label to understand the product.

For the prescripted demo, Barth syndrome returns elamipretide as an already
tried program. That is marked `NOT_A_GAP`, not because it is uninteresting, but
because the demo is trying to find gaps where an existing program has not
already covered the disease.

The live option currently checks ClinicalTrials.gov for a disease name. It does
not yet make the full target-to-program-to-approval gap claim because the live
Open Targets and Convoke joins are intentionally not claimed until they are
wired and reproducible.

## The GAP Lane

The GAP lane is the rule system behind the Disease Search table. It asks whether the
biology points to a target, whether an existing program hits that target, and
whether that disease-drug pair has already appeared in registered trials.

The rules are deterministic. A model does not decide whether something is a
gap. A model does not fix target names. If a target name cannot be reconciled by
exact match or by the closed alias table, the row abstains.

The current validation result is useful because it is negative: Barth syndrome
plus elamipretide fires `G004_ALREADY_TRIED`, so it is `NOT_A_GAP`.

## The Cell-Perturbation Figure

The figure shows a measured cell state moving away from a reference/control
state, then ranks candidate profiles by how much closer they sit to the
reference. This is a phenotype-restoration benchmark.

It is not proof of rescue, treatment, or efficacy. It is a reproducible
calculation over processed public profiles.

## The Custody Story

Every important object gets a hash. A hash acts like a fingerprint for the exact
bytes used. The graph links sources, calculations, claims, agent outputs, model
objects, and integration objects.

If a record changes, its hash changes. If someone edits a record without
updating the chain, the browser verification fails. That is the point of the
tamper demo.

## What FCO And FCG Mean Here

An FCO is a Fractal Custody Object: one content-addressed object with its own
identity, inputs, output, and custody fields.

An FCG is a Fractal Custody Graph: the linked set of those objects, where every
node can be checked and every claim points back to the evidence it consumed.

For the OpenAI fan-out, each subagent response is an FCO. The OpenAI model used
is also an FCO. The integration step that binds those outputs into the dashboard
is an FCO too.

## Claims We Can Say Out Loud

- This is a reproducible evidence-chain demo.
- This is a phenotype-first repurposing hypothesis workflow.
- The dashboard can verify its own local custody database.
- The Disease Search view can show a disease-first prescripted case and a conservative
  live ClinicalTrials probe.
- The OpenAI subagents were recorded as custody objects; the API key was not
  recorded or committed.

## Claims We Must Not Say

- Do not say this proves therapeutic efficacy.
- Do not say this proves biological rejuvenation.
- Do not say this is measured rescue.
- Do not say this is a legal freedom-to-operate opinion.
- Do not say the full Convoke/Open Targets live pipeline is wired unless the
  live demo actually shows it.

## Slide-Friendly Punchline

The demo answers three questions:

1. Did a candidate move the measured cell state back toward the reference?
2. Why do we believe the evidence chain?
3. Can another person reproduce or detect tampering in the record?
## The Model Trace

The Model Trace view answers a simple question: which models touched this demo,
and did any of them create the scientific evidence?

OpenAI models were used to run bounded helper agents. Their job was navigation:
summarize what to show, propose updates, and record evidence boundaries. Each
helper output is stored as a custody object.

Local Ollama models are inventoried by size so the team can show what could run
locally. They are not counted as scientific data sources unless a receipt says
they actually ran.

The null comparison is intentionally conservative. In the tiny cached benchmark,
the known pair did not beat the shuffle null. That is a useful negative result,
not a failure to hide.
