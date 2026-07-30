# SE v0.76

Reference implementation for nested-subject existence evolution simulation.

## Current bounded result

The D3-R functional-regulatory paired screen is complete:

- all eight fixed-checkpoint seed panels are eligible;
- physiology-output neutralization is confirmed in every intervention branch;
- six of eight seed effects reduce cumulative oxygen uptake;
- the equal-seed median relative decrease is about 0.011%, below the preregistered 2% threshold.

D3-R stops before replication. It bounds the declared acute physiology-output path but does not establish a universal zero effect for functional modules.

## Family funnel

After a manipulation-confirmed bounded-path negative, the same mechanism-family revision cannot continue with another bounded child. It must first run one aggregate gate. A manipulation-confirmed terminal negative aggregate gate closes the family revision; reopening requires a higher revision and a new directly measurable interface.

## Next candidate

D3-S tests the aggregate functional-module path using the same fixed tick-480 checkpoints:

```bash
se-exploration-candidate-record \
  --assessment analyses/d3r_functional_regulatory_paired_screen/paired_exploration_assessment.json \
  --candidate-spec protocols/candidates/d3r_functional_regulatory_oxygen_acute_effect.json \
  --ledger analyses/exploration_candidate_ledger.json

se-exploration-paired-plan \
  --stage screen \
  --candidate-spec protocols/candidates/d3s_functional_modules_harvest_acute_effect.json \
  --source-root analyses/d3n_screen \
  --checkpoint-tick 480 \
  --output analyses/d3s_functional_modules_paired_screen \
  --decision-ledger analyses/exploration_candidate_ledger.json \
  --backend auto

se-exploration-paired \
  --plan analyses/d3s_functional_modules_paired_screen/paired_exploration_plan.json
```

D3-S uses cumulative total harvest over 120 ticks and a preregistered 2% practical-effect threshold. It does not rerun shared prehistory or authorize large-scale long-term execution.

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
- [Implementation report](docs/v0.76/IMPLEMENTATION_REPORT.md)
- [D3-R supplied candidate decision](docs/v0.76/D3R_SUPPLIED_CANDIDATE_DECISION.md)
- [D3-S aggregate gate](docs/v0.76/D3S_FUNCTIONAL_MODULES_AGGREGATE_GATE.md)
- [Candidate decision ledger](docs/v0.76/SUPPLIED_CANDIDATE_LEDGER.md)
- [Protocol audit](docs/v0.76/protocol_audit.md)
