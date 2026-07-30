# Paired exploration portfolio audit

Schema: `paired-exploration-portfolio-audit-v1`
Portfolio state: `promoted-candidate-open`
Decision baseline: `package:se/resources/exploration_candidate_ledger.json`
Workspace hydration required: `True`

## Candidate specifications

| Candidate | Family | Revision | Role | Status | Recorded stages |
|---|---|---:|---|---|---|
| resource-affinity-acute-effect | resource-affinity | 1 | bounded-output-path | terminal-recorded | screen |
| elastic-capacity-use-acute-effect-v1 | knowledge-policy | 1 | component-gate | terminal-recorded | screen |
| knowledge-policy-harvest-acute-effect-v1 | knowledge-policy | 1 | aggregate-path-gate | terminal-recorded | screen |
| functional-regulatory-oxygen-uptake-acute-effect-v1 | functional-modules | 1 | bounded-physiology-output-path | terminal-recorded | screen |
| functional-modules-harvest-acute-effect-v1 | functional-modules | 1 | aggregate-path | terminal-recorded | screen |
| spatial-processing-conversion-acute-effect-v1 | spatial-processing-support | 1 | aggregate-path-gate | open-recorded | replication, screen |

## Mechanism-family revisions

| Family | Revision | Status | Closed by |
|---|---:|---|---|
| functional-modules | 1 | closed | functional-modules-harvest-acute-effect-v1 |
| knowledge-policy | 1 | closed | knowledge-policy-harvest-acute-effect-v1 |
| resource-affinity | 1 | open | - |
| spatial-processing-support | 1 | aggregate-gate-recorded | - |

## Governance decision

- next action: plan only the next ledger-authorized disjoint-seed stage
- unrecorded candidate specs: []
- open candidates: ['spatial-processing-conversion-acute-effect-v1']
- conflicts: []
- workspace ledger entries: 0
- immutable baseline entries: 7
- effective merged entries: 7
- no threshold, horizon, seed, or family status is changed by this audit
- feedback to world: false
