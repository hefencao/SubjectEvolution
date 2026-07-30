# SE v0.74

Reference implementation for nested-subject existence evolution simulation.

## Current bounded result

The D3-P elastic-capacity paired screen is complete:

- eight of eight fixed-checkpoint seed panels are eligible;
- capacity-expression neutralization is confirmed in every intervention branch;
- seed effects split four positive and four negative;
- the equal-seed median relative effect is about 0.24%, below the preregistered 5% threshold.

The candidate is terminal and does not enter replication. The result distinguishes successful target manipulation from failure of the downstream practical-effect gate.

## Next candidate

D3-Q tests the broader knowledge-policy path using the same fixed tick-480 checkpoints:

```bash
se-exploration-candidate-record \
  --assessment analyses/d3p_capacity_paired_screen/paired_exploration_assessment.json \
  --ledger analyses/exploration_candidate_ledger.json

se-exploration-paired-plan \
  --stage screen \
  --candidate-spec protocols/candidates/d3q_knowledge_policy_harvest_acute_effect.json \
  --source-root analyses/d3n_screen \
  --checkpoint-tick 480 \
  --output analyses/d3q_knowledge_policy_paired_screen \
  --decision-ledger analyses/exploration_candidate_ledger.json \
  --backend auto

se-exploration-paired \
  --plan analyses/d3q_knowledge_policy_paired_screen/paired_exploration_plan.json
```

The primary estimand is cumulative total harvest over 120 ticks. A seed is eligible only when the knowledge-policy residual changes at least one baseline action and changes no intervention actions.

## Validation workflow

```bash
make conda-sync
make test
make parity
make conda-check
```

## Current documents

- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Implementation report](docs/v0.74/IMPLEMENTATION_REPORT.md)
- [D3-P supplied candidate decision](docs/v0.74/D3P_SUPPLIED_CANDIDATE_DECISION.md)
- [D3-Q candidate protocol](docs/v0.74/D3Q_KNOWLEDGE_POLICY_CANDIDATE_PROTOCOL.md)
- [Protocol audit](docs/v0.74/protocol_audit.md)
