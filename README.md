# SE v0.75

Reference implementation for nested-subject existence evolution simulation.

## Current bounded result

The D3-Q complete knowledge-policy paired screen is complete:

- all eight fixed-checkpoint seed panels are eligible;
- knowledge-policy disablement is confirmed in every intervention branch;
- seven of eight seed effects reduce cumulative harvest;
- the equal-seed median relative effect is about -0.685%, below the preregistered 2% threshold.

The candidate stops before replication. Because D3-Q was the manipulation-confirmed aggregate gate for the current `knowledge-policy` mechanism-family revision, further internal knowledge-policy component screens are blocked unless a higher family revision and explicit new scientific rationale are preregistered.

## Next candidate

D3-R tests a separate functional-regulatory path using the same fixed tick-480 checkpoints:

```bash
se-exploration-candidate-record \
  --assessment analyses/d3q_knowledge_policy_paired_screen/paired_exploration_assessment.json \
  --candidate-spec protocols/candidates/d3q_knowledge_policy_harvest_acute_effect.json \
  --ledger analyses/exploration_candidate_ledger.json

se-exploration-paired-plan \
  --stage screen \
  --candidate-spec protocols/candidates/d3r_functional_regulatory_oxygen_acute_effect.json \
  --source-root analyses/d3n_screen \
  --checkpoint-tick 480 \
  --output analyses/d3r_functional_regulatory_paired_screen \
  --decision-ledger analyses/exploration_candidate_ledger.json \
  --backend auto

se-exploration-paired \
  --plan analyses/d3r_functional_regulatory_paired_screen/paired_exploration_plan.json
```

The primary estimand is cumulative realized oxygen uptake over 120 ticks. A seed is eligible only when baseline functional regulatory output is non-zero and the intervention branch records zero regulatory-output dimensions and zero changed-entity fraction.

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
- [Implementation report](docs/v0.75/IMPLEMENTATION_REPORT.md)
- [D3-Q supplied candidate decision](docs/v0.75/D3Q_SUPPLIED_CANDIDATE_DECISION.md)
- [D3-R candidate protocol](docs/v0.75/D3R_FUNCTIONAL_REGULATORY_CANDIDATE_PROTOCOL.md)
- [Candidate decision ledger](docs/v0.75/SUPPLIED_CANDIDATE_LEDGER.md)
- [Protocol audit](docs/v0.75/protocol_audit.md)
