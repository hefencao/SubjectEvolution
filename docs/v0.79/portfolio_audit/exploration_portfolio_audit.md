# Paired exploration portfolio audit

Schema: `paired-exploration-portfolio-audit-v1`
Portfolio state: `candidate-specs-awaiting-assessment`
Decision baseline: `package:se/resources/exploration_candidate_ledger.json`
Workspace hydration required: `False`

## Candidate specifications

| Candidate | Family | Revision | Role | Status | Recorded stages |
|---|---|---:|---|---|---|
| elastic-capacity-use-acute-effect-v1 | knowledge-policy | 1 | component-gate | terminal-recorded | screen |
| knowledge-policy-harvest-acute-effect-v1 | knowledge-policy | 1 | aggregate-path-gate | terminal-recorded | screen |
| functional-regulatory-oxygen-uptake-acute-effect-v1 | functional-modules | 1 | bounded-physiology-output-path | terminal-recorded | screen |
| functional-modules-harvest-acute-effect-v1 | functional-modules | 1 | aggregate-path | terminal-recorded | screen |
| spatial-processing-conversion-acute-effect-v1 | spatial-processing-support | 1 | aggregate-path-gate | awaiting-assessment | - |

## Mechanism-family revisions

| Family | Revision | Status | Closed by |
|---|---:|---|---|
| functional-modules | 1 | closed | functional-modules-harvest-acute-effect-v1 |
| knowledge-policy | 1 | closed | knowledge-policy-harvest-acute-effect-v1 |
| resource-affinity | 1 | open | - |

## Governance decision

- next action: record or execute the listed preregistered candidate specifications
- unrecorded candidate specs: ['spatial-processing-conversion-acute-effect-v1']
- open candidates: []
- conflicts: []
- workspace ledger entries: 5
- immutable baseline entries: 5
- effective merged entries: 5
- no threshold, horizon, seed, or family status is changed by this audit
- feedback to world: false
