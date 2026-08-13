# Disease Search Component

Internal source note: this came from the teammate handoff labelled "Elvis."
The demo label is **Disease Search**.

The teammate handoff pivots the demo from compound-first to disease-first.

## Component Contract

Input:

- Rare disease name, primary path.
- Target symbol, secondary path.

Output:

- One table row per disease, target, drug-program pairing.
- Deterministic grade: `GAP`, `NOT_A_GAP`, or abstention.
- Always-visible abstention counts.
- Custody click-through to hashed evidence.
- Claim ceiling: `REPURPOSING_HYPOTHESIS`.

## Demo Modes

### Prescripted

The prescripted mode is the Barth/elamipretide validation case from the
handoff. It is guaranteed to work without network access and proves that the
prior-trial filter marks the incumbent as:

```text
G004_ALREADY_TRIED / NOT_A_GAP
```

### Live

The live option calls the local Python server:

```text
/api/elvis?q=<disease>
```

This is intentionally conservative. It probes the live ClinicalTrials.gov
condition endpoint and returns rows or abstentions. It does not claim the full
Open Targets -> Convoke -> ClinicalTrials -> openFDA gap lane is wired until
Convoke endpoint, query grammar, stability, and license terms are documented.

## Why This Fits Protein Hinge

The CPJUMP1 morphology result becomes a detail/evidence lane. The first screen
becomes disease-first:

```text
disease -> targets/programs/trials -> deterministic grade -> custody chain
```

The custody machinery remains unchanged: FCG/FCO records are still the durable
proof surface, and claim ceilings stay explicit.
