# SE v0.79

Reference implementation for nested-subject existence evolution simulation.

## Current bounded result

The supplied portfolio audit is correct: the immutable and workspace histories both contain the established five terminal decisions, no candidate identity conflicts exist, and the v0.78 shipped portfolio is genuinely exhausted.

v0.79 therefore performs a scientific revision rather than another ledger repair or a rerun of a closed family. It preregisters D3-T, a new `spatial-processing-support` family that tests the direct conserved interface from phase-shifted local processing support to realized raw-resource conversion.

D3-T preserves genotype, stores, resource fields, residue, per-unit processing cost, checkpoints and random streams. Its primary metric is cumulative converted resource over 120 ticks with a 2% practical-effect threshold. A new demand-weighted absolute support-deviation metric proves that baseline entities actually encounter non-neutral support and that the intervention removes that exposure.

The candidate does not establish movement response, ecological specialization, stable niches or long-horizon selection.

## Suggested commands

The package version and reporting schema changed, so update the editable Conda installation first:

```bash
make conda-sync

se-exploration-portfolio-audit \
  --ledger analyses/exploration_candidate_ledger.json \
  --candidate-dir protocols/candidates \
  --output analyses/exploration_portfolio_audit

se-exploration-paired-plan \
  --stage screen \
  --candidate-spec protocols/candidates/d3t_spatial_processing_conversion_acute_effect.json \
  --source-root analyses/d3n_screen \
  --checkpoint-tick 480 \
  --output analyses/d3t_spatial_processing_conversion_paired_screen \
  --decision-ledger analyses/exploration_candidate_ledger.json \
  --backend auto

se-exploration-paired \
  --plan analyses/d3t_spatial_processing_conversion_paired_screen/paired_exploration_plan.json
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
- [Implementation report](docs/v0.79/IMPLEMENTATION_REPORT.md)
- [Governance check](docs/v0.79/GOVERNANCE_CHECK.md)
- [Supplied portfolio audit](docs/v0.79/SUPPLIED_PORTFOLIO_AUDIT.md)
- [Protocol audit](docs/v0.79/protocol_audit/protocol_audit.md)
- [Current portfolio audit](docs/v0.79/portfolio_audit/exploration_portfolio_audit.md)
