# SE v0.80

Reference implementation for nested-subject existence evolution simulation.

## Current bounded result

The supplied D3-T eight-seed screen is valid. Every manipulation contract passes, all eight seed-level effects have the same sign, and neutralizing spatial processing support increases cumulative realized resource conversion by a median of about **3.03%**, above the preregistered 2% threshold.

This is a promotion-positive acute screen, not a long-horizon selection result. It shows that the existing phase-shifted support interface materially changes conversion on the fixed D3-N tick-480 source panel. Because the intervention effect is positive, the active support surface is acutely suppressive on this estimand in these checkpoints; that direction must replicate rather than be explained post hoc.

v0.80 records the screen and prepares a protocol-locked disjoint-seed replication. Replication changes only the independent seed set. The former larger-world replication configuration is retained as an unregistered scale-robustness configuration and is rejected by the replication planner.

## Suggested commands

The package version, source-plan schema and decision baseline changed, so update the editable Conda installation first:

```bash
make conda-sync

se-exploration-candidate-record \
  --assessment analyses/d3t_spatial_processing_conversion_paired_screen/paired_exploration_assessment.json \
  --candidate-spec protocols/candidates/d3t_spatial_processing_conversion_acute_effect.json \
  --ledger analyses/exploration_candidate_ledger.json

se-exploration-plan \
  --stage replication \
  --candidate spatial-processing-conversion-acute-effect-v1 \
  --config configs/mvp_d3n_exploration_replication.json \
  --seeds 71201,71202,71203,71204,71205,71206,71207,71208 \
  --output analyses/d3n_replication \
  --backend auto \
  --until-tick 480 \
  --prior-plan analyses/d3n_screen/exploration_plan.json
```

Execute the `se-multi` command written to `analyses/d3n_replication/exploration_plan.md`, then create and run the matched replication panel:

```bash
se-exploration-paired-plan \
  --stage replication \
  --candidate-spec protocols/candidates/d3t_spatial_processing_conversion_acute_effect.json \
  --source-root analyses/d3n_replication \
  --checkpoint-tick 480 \
  --prior-assessment analyses/d3t_spatial_processing_conversion_paired_screen/paired_exploration_assessment.json \
  --output analyses/d3t_spatial_processing_conversion_paired_replication \
  --decision-ledger analyses/exploration_candidate_ledger.json \
  --backend auto

se-exploration-paired \
  --plan analyses/d3t_spatial_processing_conversion_paired_replication/paired_exploration_plan.json
```

## Validation workflow

```bash
make test
make conda-check
make parity-gpu
```

`make parity-gpu` is a target-device release gate and intentionally fails when no usable CUDA/CuPy device is present.

## Current documents

- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Recurring governance check](docs/PROJECT_GOVERNANCE.md)
- [Implementation report](docs/v0.80/IMPLEMENTATION_REPORT.md)
- [Governance check](docs/v0.80/GOVERNANCE_CHECK.md)
- [Supplied D3-T assessment](docs/v0.80/D3T_SUPPLIED_ASSESSMENT.json)
- [Protocol audit](docs/v0.80/protocol_audit/protocol_audit.md)
- [Current portfolio audit](docs/v0.80/portfolio_audit/exploration_portfolio_audit.md)
