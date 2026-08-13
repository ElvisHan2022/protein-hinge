# Freedom-to-Operate design

**Status:** design, not an opinion. **Ceiling:** `CLEARANCE_SEARCH_RECORD`.
**Nobody here is a lawyer.** Nothing in this directory is legal advice.

---

## 0. What this is, and the one thing it must never become

A freedom-to-operate opinion is a legal instrument. It is written by qualified
patent counsel, it carries their name, and it is the thing a company relies on
when it decides to spend money. This repository cannot produce one and must not
appear to.

What this repository produces is the layer underneath: a **structured,
reproducible, hash-pinned record of what was searched, when, where, with what
query, and what came back.** That record is the raw material counsel works
from. Handing counsel a good one shortens the engagement and lowers the bill.
Handing counsel a confident conclusion we were not qualified to reach wastes
their time and creates liability for us.

So the FTO lane reuses the custody graph's claim grammar without modification,
and it caps lower than the science lane does:

| Level | Meaning in the FTO lane | Who can issue it |
|---|---|---|
| `COMMITTED` | A search was run and its results were hashed. Nobody read them. | this system |
| `RECOMPUTED` | The search is reproducible: same query, same corpus snapshot, same result digest. | this system |
| `SCREENED` | A human read the results and triaged them into blocking / adjacent / irrelevant. | a named human on the team |
| `CLEARANCE_SEARCH_RECORD` | The complete, reproducible, human-triaged search file. **The ceiling.** | this system + named human |
| `FTO_OPINION` | A legal conclusion about infringement risk. | **outside counsel only. Never us.** |

`FTO_OPINION` exists in the enum for exactly one reason: so that the code can
refuse to emit it. Same pattern as `AUTHENTICATED` and `VALIDATED` in `fcg.py` —
a level you cannot label yourself with is a level you cannot quietly assume.

---

## 1. Reading of the acronym

"FTC/FTO" has two plausible readings and both turn out to matter, so both are
in scope. They are separate lanes because they fail for separate reasons.

**Freedom to Operate (FTO)** — can we make, use, or sell this without
infringing someone's patent? This is the dominant reading in biopharma and it
is the bulk of this document.

**Freedom to Commercialize (FTC)** — the downstream gate. Even with clean FTO,
commercialization can be blocked by regulatory exclusivity, by data licensing
terms, or by the substantiation standard for the claims we make in marketing.
That last one is also, confusingly, an FTC matter in the other sense: the U.S.
Federal Trade Commission polices health-benefit claims and requires competent
and reliable scientific evidence behind them. Our claim-ceiling machinery is
already built for precisely that discipline. §6 covers it.

If you meant something else by FTC, say so and this section gets rewritten.

---

## 2. Three lanes, cleared independently

The single most common FTO mistake on a project like this is to treat it as one
question. It is three, they have different answers, and a clean answer in one
lane tells you nothing about the others.

```
   LANE D — DATA                LANE M — METHOD              LANE C — COMPOUND
   may we use the inputs?       may we run and sell          may we develop the
                                the pipeline?                molecule we find?

   JUMP cpg0016 profiles        ranking method               composition of matter
   JUMP metadata                normalization scheme         method of treatment
   Cell Painting Gallery        software/algorithm IP        formulation / dosing
   partner artifacts            trade secret posture         regulatory exclusivity

   status: RESOLVED-CLEAN       status: OPEN                 status: OPEN, and the
   (see §3)                     (see §4)                     hard one (see §5)
```

Lane D is closed. Lanes M and C are open and stay open. A project that reports
"FTO: clear" without saying which lane is not reporting anything.

---

## 3. Lane D — the data. Resolved.

Every byte this project consumes is Cell Painting Gallery data, released under
**CC0 1.0 Universal** — a public-domain dedication, not a restrictive license.
There is no field-of-use limit, no non-commercial clause, and no share-alike
obligation. Commercial use is permitted.

Two consequences worth stating plainly, because they are routinely confused:

**Citation is an ethical obligation, not a license condition.** CC0 waives the
attribution requirement. We cite anyway — the JUMP dataset paper and the Cell
Painting Gallery paper (Weisbart et al., 2024) — because not citing is
misconduct even when it is not infringement. The custody graph enforces this
mechanically: every source node carries its origin URI and digest, so the
citation cannot drift from the thing actually used.

**CC0 on the data says nothing about the compounds.** The TARGET2 library
contains real molecules with real owners. That a morphological profile is
public domain does not make the molecule it depicts free to develop. Lane D
clearing has zero carry-over into Lane C. This is the trapdoor.

The partner artifacts pulled from `biobitworks/aws-biopharma` are pinned by
digest and marked `"adopted": false` in the graph. Pinning records what they
served us. It does not license their content and does not adopt their claims.
Their license terms are an open item on the checklist.

---

## 4. Lane M — the method

The pipeline is: consensus counter-perturbation ranking of Cell Painting
profiles against a multi-gene knockout axis. The FTO surface here is narrower
than people expect but is not empty.

What to search, in descending order of how much it would hurt:

1. **Method-of-screening claims** — "a method of identifying a therapeutic
   candidate comprising comparing a compound-induced morphological profile to a
   genetic-perturbation profile." This is the shape that would reach us
   directly. Connectivity-mapping and morphological-profiling method patents
   are a real, populated space.
2. **Cell Painting assay claims** — the staining protocol itself. We do not run
   the assay; we consume profiles someone else generated. This is likely
   irrelevant to us, but "likely" is a search result, not an assumption.
3. **Software and pipeline claims** — generally weak post-*Alice* for abstract
   data-comparison steps, but weak is not zero.

The defensive posture that actually matters: the method as described is
**published prior art by construction.** The consensus-axis approach, the
normalization frame, and the ranking metric are all written into
`HACKDAY_STATE.yaml`, which is hashed into the graph with a fixed timestamp and
a reproducible root. A dated, hash-pinned, publicly reproducible description is
the cheapest defensive-publication instrument that exists. It cannot clear
existing patents, but it raises the bar against future ones covering the same
ground.

---

## 5. Lane C — the compound. The hard one.

This lane decides whether the project has a future, and it contains the single
most important distinction in the whole design.

### 5.1 We are not making SS-31. That is the whole point.

Elamipretide (SS-31, formerly MTP-131 / Bendavia) is a Szeto–Schiller
tetrapeptide owned by Stealth BioTherapeutics. It received FDA accelerated
approval in September 2025 for Barth syndrome in patients ≥30 kg, marketed as
FORZINITY — the first disease-specific treatment for Barth syndrome.

Composition-of-matter patents on that peptide are the strongest rights in this
space, and they **do not reach us**, because the project's entire premise is
that we are looking for a structurally unrelated small molecule. The peptide is
not in the JUMP library, is never a comparator, and is never a synthesis
target. It is the motivation and nothing else.

This is not a loophole. It is the difference between copying a drug and finding
a different one for the same problem, and it is the ordinary way second-entrant
programs work.

### 5.2 What does reach us

**Method-of-treatment claims.** This is the live risk. A claim of the form
"a method of treating Barth syndrome comprising administering an agent that
[interacts with cardiolipin / stabilizes cristae / improves mitochondrial
membrane function]" is not limited to a peptide. If such a claim is granted and
in force, it can reach a small molecule that has nothing structurally in common
with SS-31. **Search method-of-treatment claims before, not after, you get
attached to a hit.**

**Rights on the hit itself.** Any TARGET2 compound that ranks well is an
existing molecule with an existing owner and an existing patent history. The
FTO question is not about the library, it is about the specific molecule, and
it cannot be answered until there is a ranked list. Each candidate needs its
own lane-C file.

**Orphan drug exclusivity.** Elamipretide holds FDA orphan designation for
Barth syndrome, which confers seven years of market exclusivity from approval —
running to approximately **September 2032**.

The scope of that exclusivity is narrow in a way that matters enormously here,
and getting it wrong in either direction sinks the project:

| Blocked | Not blocked |
|---|---|
| FDA approval of the *same drug* for the *same* orphan indication | Research. Exclusivity is a marketing bar, not a research bar. |
| — | A *structurally different* drug for the same indication. |
| — | The same indication if you demonstrate clinical superiority. |
| — | *Different* indications entirely. |

A different small molecule for Barth syndrome is not blocked by elamipretide's
orphan exclusivity. Read the second column carefully before anyone concludes
the window is shut — and then have counsel confirm it, because this paragraph
is a research note, not an opinion.

### 5.3 The adjacent-indication question

SS-31 is a subcutaneous injectable and does not cross the blood–brain barrier,
which puts Leigh syndrome and MELAS out of its reach. If a small-molecule hit
were orally available or CNS-penetrant, it would be addressing populations
elamipretide structurally cannot serve. That is a different indication, a
different exclusivity analysis, and a stronger commercial position.

It is also a much bigger claim than anything the data can currently support, so
it lives here as a search direction and nowhere else. It is not in
`HACKDAY_STATE.yaml` and must not migrate into any output.

---

## 6. Freedom to Commercialize — the substantiation gate

Distinct from patents. Even a clean FTO does not license the *claims* we make.

U.S. FTC standards for health-benefit advertising require competent and
reliable scientific evidence behind a claim, proportional to how strong the
claim is. Our claim grammar was built for the same discipline, so the mapping
is direct and the ceiling is already correct:

| What we could say | Backed by | Permitted |
|---|---|---|
| "predicted to counter-perturb the cardiolipin-module signature" | ranked cosine + disclosed null | yes, at ceiling |
| "cardiolipin binder" | nothing. no binding assay was run. | **no** |
| "SS-31 mimetic" | nothing. SS-31 was never a comparator. | **no** |
| "rescues" / "treats" Barth syndrome | nothing. no cells, no animals, no patients. | **no** |

`HACKDAY_STATE.yaml` already bans these strings and caps the project at
`REPURPOSING_HYPOTHESIS`. That ceiling is not modesty theatre — it is the same
line the FTC would draw, drawn early, in a place where the code can enforce it.

**Predicted counter-perturbation is not measured rescue.** It is written into
every claim node the graph emits.

---

## 7. How FTO lives in the custody graph

No new machinery. FTO uses the existing node kinds, so an FTO finding is
admitted, routed, and tamper-checked exactly like a profile digest.

```
LAYER 0   FTO_SOURCE       a search result set, hashed at the point of origin
                           custody: {registry, query_string, corpus_date,
                                     result_count, uri, sha256}
                           evidence: COMMITTED  (we hold a digest, not a right)

LAYER 1   FTO_SEARCH       a named, replayable query over a named corpus
                           recompute: {registry, query, filters, date_bounds}
                           inputs:    the FTO_SOURCE nodes it returned

LAYER 2   FTO_TRIAGE       a human read the results and sorted them
                           custody: {reviewer, reviewed_at, n_blocking,
                                     n_adjacent, n_irrelevant}
                           evidence: SCREENED  (requires a named human)

LAYER 3   FTO_FINDING      "lane D is clear because the data is CC0"
                           ceiling: CLEARANCE_SEARCH_RECORD
                           the module REFUSES to emit FTO_OPINION
```

Two properties fall out of reusing the graph, and both are the actual argument
for doing it this way:

**A stale search is visibly stale.** `corpus_date` is inside the node body, and
the node id is the hash of the body. A search run last month and a search run
today are different nodes with different ids. There is no way to quietly reuse
an old clearance.

**A finding cannot outlive its inputs.** If a search node is superseded, every
finding downstream of it is rejected automatically by the same `admit()`
recursion that governs the science lane. Rule R2 — reject, do not annotate —
applies without modification. You cannot leave a stale clearance sitting in the
graph with a warning sticker on it.

---

## 8. Directory structure

```
biocustody/
  fcg/
    fcg.py               the custody store: nodes, admission, RFC 6962 merkle
    ingest.py            layer 0-3 for the science lane
    tamper_test.py       two-arm attack: bytes-only, and the cover-up
    origin_digests.json  JUMP + partner digests, hashed at origin
    store/               nodes/ atoms/ routes/ merkle_receipt.json index.json
  fto/
    FTO_DESIGN.md        this file
    fto.py               registries, node constructors, the FTO_OPINION refusal
    registry_digests.json  live query digests + extracted findings
    ingest_fto.py        attaches the FTO lane to the science graph
```

Both lanes land under **one Merkle root**. That is deliberate: the provenance
of "who else is working on this" is held to the same standard as the provenance
of a parquet file, and a single receipt covers both.

Per-candidate compound rights are not represented yet and will not be until
Phase 1 produces a ranking. Searching compound rights before there are
compounds is theatre.

---

## 9. Registries wired, and what they returned

Four public corpora are queried and hashed at origin; two are listed and not
wired. Full digests and per-query results are in `registry_digests.json`; the
searches, triages, and findings are live nodes in the graph.

| Registry | Lane | Status | What it answered |
|---|---|---|---|
| ClinicalTrials.gov | C | wired | who else is in the clinic |
| openFDA (label, NDC) | C | wired | what the incumbent label covers |
| Open Targets | C | wired | is the target tractable at all |
| FDA Orphan Drug designation DB | C | **not wired** | no stable API; web form only |
| Convoke | C | **not wired** | needs `CONVOKE_MCP_TOKEN`, which is not ours |

Convoke stays out until someone with access documents its query surface and
the license on what it returns. An undocumented source cannot be admitted,
because nobody else can recompute a result from it. That is rule R1, not a
preference. The token belongs in `.env` and never in this repo.

### 9.1 The competitive field is one company

Eleven registered Barth syndrome studies. The only sponsor running
interventional drug trials is Stealth BioTherapeutics: NCT03098797 (Ph2/3,
completed), NCT07531251 (Ph4, recruiting, "4TAZPower"), and NCT04689360
(intermediate-size expanded access). Everything else is a registry, a
natural-history cohort, an exercise study, or a text-match false positive.

**No competing small-molecule program is registered.** Read that carefully:
ClinicalTrials.gov registers *trials*, not *programs*. Preclinical and
discovery work is invisible here. Absence of a registered competitor is weak
evidence of no competitor, and it is recorded in the graph with that caveat
attached to the node rather than as a footnote someone can drop.

### 9.2 The finding that most affects the project

Open Targets was queried for all eight consensus genes. **Every one returns
zero small-molecule tractability buckets and zero drug or clinical candidates.**

That number is only meaningful if the field works, so EGFR was queried with the
identical query as a positive control: five SM buckets (Approved Drug,
Structure with Ligand, High-Quality Ligand, High-Quality Pocket, Druggable
Family) and 82 drug candidates. The field populates. The zeros are real.

This cuts hard in both directions, and the project is only honest if it says
both out loud:

**It is the strongest available argument for the method.** You cannot run
structure-based design against a protein with no ligandable pocket. A
phenotype-first ranking does not need one — it scores compounds by the
morphology they produce, whatever they happen to bind. The absence of
tractability is precisely why the conventional route was never taken here, and
precisely why an unconventional one is worth trying.

**It is also the sharpest caveat on any result.** There is no reference
chemistry against this module. No positive-control compound exists to validate
the axis, and no prior art exists to sanity-check a hit against. Any ranking
this pipeline produces will be mechanistically unexplained, and there is
nothing in the literature to catch it if it is wrong.

Open Targets evidence is genetic, literature, and pathway derived. None of it
comes from Cell Painting, so agreement between the two is corroboration rather
than the same signal counted twice. That orthogonality is the whole reason to
wire it.

---

## 10. Checklist state

| # | Item | Lane | State |
|---|---|---|---|
| 1 | Cell Painting Gallery / cpg0016 license is CC0 1.0 | D | **CLEAR** |
| 2 | Citation obligations identified (JUMP paper, Weisbart 2024) | D | **CLEAR** |
| 3 | Partner artifact license terms (`biobitworks/aws-biopharma`) | D | **OPEN** — pinned, not licensed |
| 4 | Morphological-profiling method-claim search | M | **NOT STARTED** |
| 5 | Defensive publication of the method via hashed state file | M | **IN PLACE** — root reproducible |
| 6 | SS-31 composition-of-matter does not reach a small molecule | C | **CLEAR** — different chemical matter |
| 7 | Method-of-treatment claims naming Barth / cardiolipin | C | **NOT STARTED** — highest priority |
| 8 | Orphan exclusivity scope (approval bar, not research bar) | C | **RESEARCH NOTE** — needs counsel |
| 9 | Competitive landscape via ClinicalTrials.gov | C | **SCREENED** — one company, weak-evidence caveat recorded |
| 10 | Incumbent label via openFDA | C | **SCREENED** — label + 7 NDC entries |
| 11 | Target tractability via Open Targets | C | **SCREENED** — 0/8 tractable, EGFR control passed |
| 12 | FDA orphan designation database | C | **NOT WIRED** — no stable API |
| 13 | Convoke | C | **NOT WIRED** — token not ours, surface undocumented |
| 14 | Per-candidate rights | C | **BLOCKED** — no ranking yet |
| 15 | Claim ceiling enforced in code | FTC | **IN PLACE** — banned strings + `add_claim` and `emit_finding` refusals |

Items 4 and 7 are the two that would change the shape of the project. Neither
has been started. That is the honest state and it is stated here rather than
buried.

---

## 11. Stop conditions

Stop and escalate to a human, and then to counsel, if any of these occur:

- a granted, in-force method-of-treatment claim is found that plausibly reads
  on a small molecule for Barth syndrome or for cardiolipin-pathway disease
- a top-ranked candidate turns out to be under active development by another
  party for a mitochondrial indication
- anyone proposes to state a conclusion at `FTO_OPINION`
- anyone proposes to relax the `REPURPOSING_HYPOTHESIS` ceiling on the basis of
  an FTO result — FTO and scientific claim strength are unrelated, and coupling
  them is how overclaiming starts
- a partner artifact turns out to carry license terms incompatible with CC0
  downstream use

---

## Sources

- [Elamipretide: First Approval — Drugs (Springer)](https://link.springer.com/article/10.1007/s40265-025-02269-8)
- [Stealth BioTherapeutics — FDA acceptance of elamipretide NDA resubmission](https://stealthbt.com/stealth-biotherapeutics-announces-fda-acceptance-of-elamipretide-nda-resubmission/)
- [Elamipretide (FORZINITY) — Friedreich's Ataxia Research Alliance](https://www.curefa.org/drug-development/elamipretide/)
- [Stealth BioTherapeutics — EMA orphan drug designation for Barth syndrome](https://www.prnewswire.com/news-releases/stealth-biotherapeutics-receives-orphan-drug-designation-from-the-european-medicines-agency-for-elamipretide-for-the-treatment-of-barth-syndrome-301303067.html)
- [Cell Painting Gallery — Registry of Open Data on AWS](https://registry.opendata.aws/cellpainting-gallery/)
- [broadinstitute/cellpainting-gallery — README](https://github.com/broadinstitute/cellpainting-gallery/blob/main/README.md)
- [Cell Painting Gallery: an open resource for image-based profiling (Weisbart et al., 2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11466682/)
- [JUMP-Cell Painting Consortium](https://jump-cellpainting.broadinstitute.org/)
- [CC0 1.0 Universal — Creative Commons](https://creativecommons.org/public-domain/#cc0)
