# SE v0.77

Reference implementation for nested-subject existence evolution simulation.

## Current bounded result

The supplied D3-S aggregate functional-module screen is complete:

- all eight fixed-checkpoint seed panels are eligible;
- complete functional-module ablation is confirmed in every intervention branch;
- seven of eight seed effects increase cumulative total harvest;
- the equal-seed median relative increase is about 0.107%, below the preregistered 2% threshold.

D3-S stops before replication and closes `functional-modules` revision 1. This is a candidate-specific acute result, not a universal claim that functional modules have no effect.

## Exploration portfolio state

The bundled candidate ledger now reports family-revision state explicitly. `knowledge-policy` revision 1 and `functional-modules` revision 1 are closed by manipulation-confirmed aggregate gates. No shipped candidate is open or awaiting assessment.

The portfolio audit therefore reports `scientific-revision-required`. Another paired plan requires either a genuinely new mechanism family or a higher closed-family revision with both:

- an explicit scientific rationale;
- a named, directly measurable interface that was not available to the closed revision.

The audit does not choose a new mechanism, lower a threshold, extend a horizon, or feed back into the world.

## Governance commands

```bash
se-exploration-candidate-record \
  --assessment analyses/d3s_functional_modules_paired_screen/paired_exploration_assessment.json \
  --candidate-spec protocols/candidates/d3s_functional_modules_harvest_acute_effect.json \
  --ledger analyses/exploration_candidate_ledger.json

se-exploration-portfolio-audit \
  --ledger analyses/exploration_candidate_ledger.json \
  --candidate-dir protocols/candidates \
  --output analyses/exploration_portfolio_audit
```

## Validation workflow

```bash
make conda-sync
make test
make conda-check
make parity-gpu
```

`make parity-gpu` is a target-device release gate and intentionally fails when no usable CUDA/CuPy device is present.

## Current documents

- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Recurring governance check](docs/PROJECT_GOVERNANCE.md)
- [Implementation report](docs/v0.77/IMPLEMENTATION_REPORT.md)
- [D3-S supplied candidate decision](docs/v0.77/D3S_SUPPLIED_CANDIDATE_DECISION.md)
- [Candidate decision ledger](docs/v0.77/SUPPLIED_CANDIDATE_LEDGER.md)
- [Exploration portfolio audit](docs/v0.77/exploration_portfolio_audit.md)
- [Protocol audit](docs/v0.77/protocol_audit.md)
- [Validation report](docs/v0.77/VALIDATION_REPORT.md)
