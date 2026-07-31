# Paired exploration candidate decision ledger

Schema: `paired-exploration-candidate-ledger-v5`

| Candidate | Family | Stage | Decision | Evidence | Eligible seeds | Manipulation | Direction | Median relative effect |
|---|---|---|---|---|---:|---:|---:|---:|
| elastic-capacity-use-acute-effect-v1 | knowledge-policy | screen | stop | manipulation-confirmed-promotion-negative | 8 | 1.0 | 0.5 | 0.0024330854786726187 |
| functional-modules-harvest-acute-effect-v1 | functional-modules | screen | stop | manipulation-confirmed-promotion-negative | 8 | 1.0 | 0.875 | 0.0010705984647323922 |
| functional-regulatory-oxygen-uptake-acute-effect-v1 | functional-modules | screen | stop | manipulation-confirmed-promotion-negative | 8 | 1.0 | 0.75 | -0.00010983013069538439 |
| knowledge-policy-harvest-acute-effect-v1 | knowledge-policy | screen | stop | manipulation-confirmed-promotion-negative | 8 | 1.0 | 0.875 | -0.006848291263809552 |
| resource-affinity-acute-effect | resource-affinity | screen | stop | promotion-negative-without-direct-manipulation-contract | 8 | None | 0.625 | 0.0033445924735386744 |
| spatial-processing-conversion-acute-effect-v1 | spatial-processing-support | confirmation | confirmed-acute | manipulation-confirmed-promotion-positive | 8 | 1.0 | 1.0 | 0.02827052106409674 |
| spatial-processing-conversion-acute-effect-v1 | spatial-processing-support | replication | promote | manipulation-confirmed-promotion-positive | 8 | 1.0 | 1.0 | 0.025460716932186538 |
| spatial-processing-conversion-acute-effect-v1 | spatial-processing-support | screen | promote | manipulation-confirmed-promotion-positive | 8 | 1.0 | 1.0 | 0.030264630111609556 |

## Mechanism-family revisions

| Family | Revision | Status | Aggregate candidates | Closed by |
|---|---:|---|---|---|
| functional-modules | 1 | closed | functional-modules-harvest-acute-effect-v1 | functional-modules-harvest-acute-effect-v1 |
| knowledge-policy | 1 | closed | knowledge-policy-harvest-acute-effect-v1 | knowledge-policy-harvest-acute-effect-v1 |
| resource-affinity | 1 | open | - | - |
| spatial-processing-support | 1 | aggregate-gate-recorded | spatial-processing-conversion-acute-effect-v1 | - |

A terminal failed candidate cannot be automatically reopened or relabeled. A changed intervention, metric, direction, threshold, horizon, or manipulation contract requires an explicit new candidate revision.

After a manipulation-confirmed bounded-path negative, the same family revision must run an aggregate gate before any additional bounded candidate. This prevents open-ended component fishing.

A manipulation-confirmed terminal aggregate-family gate can close its mechanism family. Reopening requires a higher family revision, an explicit scientific rationale, and a named directly measurable interface; relabeling a child candidate is insufficient.

Manipulation-confirmed promotion failure means the predeclared target was engaged but the candidate failed its seed-level direction or practical-effect gate. It is not a universal zero-effect claim outside that candidate specification.
