# Paper metrics — generated, do not edit by hand

Regenerate with `python3 scripts/build_paper_metrics.py`. If the paper
disagrees with this file, the paper is stale.

Corpus captured 2026-08-25T00:33:29+00:00 ·
subset `sha256:3aa5e6723563a567…` ·
variants `sha256:355d8e96bc612342…`

Reconciliation: 746 records fetched =
364 kept + 382 excluded +
0 unavailable
(**balanced**)

## Silent errors prevented

| Guard | Naive pipeline emits | Silently wrong | Rate | Enforced emits |
|---|---:|---:|---:|---:|
| G1 residue verification | 114 | **16** | **14.0%** | 98 (all verified correct) |
| G2 copy-number exclusion | 746 | **382** | **51.2%** | 364 |

G2 additionally takes **3 of 8 genes**
(PGS1, PHB2, CHCHD3) from apparent evidence to an honest
zero.

## Cost of enforcement

The sequence lane declines 266 of
364 records and emits 98. Declining everything would also score
zero silent errors, so the reasons matter:

| Reason declined | Records |
|---|---:|
| frameshift | 131 |
| no protein notation | 118 |
| residue mismatch | 16 |
| position out of range | 1 |

## Per-gene effect of G2

| Gene | Naive count | Enforced | Excluded |
|---|---:|---:|---:|
| TAFAZZIN | 339 | 109 | 230 |
| CRLS1 | 33 | 3 | 30 |
| PGS1 | 14 | 0 | 14 |
| PTPMT1 | 13 | 1 | 12 |
| HADHA | 267 | 251 | 16 |
| PHB | 0 | 0 | 0 |
| PHB2 | 46 | 0 | 46 |
| CHCHD3 | 34 | 0 | 34 |

## Not measured

- whether any proposed drug-disease pairing is biologically correct
- generalisation beyond the validation disease
- efficacy, treatment value, or clinical utility
- closed-vocabulary resolution (G3) -- reported as a worked example; n=1 in this corpus, no rate claimed
