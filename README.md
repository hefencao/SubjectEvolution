# SE v0.82

Reference implementation for nested-subject existence evolution simulation.

## Current bounded result

D3-T has completed preregistered screen, disjoint-seed replication, and exact-
protocol confirmation. All three eight-seed panels pass their manipulation
contracts and retain the same direction. In confirmation, neutralizing spatial-
processing support increases cumulative realized resource conversion by an
equal-seed median of about **2.827%**, above the unchanged 2% practical
threshold.

The candidate is terminal as `confirmed-acute`. Active support is repeatedly
suppressive on this acute estimand, but the result does not establish long-
horizon selection, adaptive benefit, stable niches, or a population source
rule. Another paired experiment requires a distinct preregistered estimand and
direct manipulation contract.

## Workspace layout

- [`studies/`](studies/README.md): study design, candidate/config protocols, ordered runbooks, and frozen evidence chains.
- [`runs/`](runs/README.md): source trajectories, intervention branches, and checkpoints.
- [`analyses/`](analyses/README.md): derived assessments, audits, and compact reports only.
- [`state/`](state/README.md): mutable local decision overlays.
- [`protocols/`](protocols/README.md): project-wide registries and immutable release decisions.
- [`configs/`](configs/README.md): reusable project-level configuration presets; study-specific configs live with their study.

## D3-T result chain

The canonical design and complete frozen screen-to-confirmation chain are under
[`studies/d3t_spatial_processing_conversion_v1/`](studies/d3t_spatial_processing_conversion_v1/README.md).

Executable commands remain isolated in numbered files under
[`studies/d3t_spatial_processing_conversion_v1/commands/`](studies/d3t_spatial_processing_conversion_v1/commands/).
The compact result import/export commands make cross-version transfer explicit;
README files do not duplicate executable command blocks.

## Compact result capability

A canonical exported result bundle contains the study definition, protocols,
frozen evidence, chain summary, and a file manifest. It is sufficient for
scientific decision import. Large checkpoints remain external and are required
only for exact replay or analyses not already frozen.

## Validation workflow

Project validation targets remain defined in the [`Makefile`](Makefile). Target-
device GPU parity remains a release gate and requires a usable CUDA/CuPy
environment.

## Current documents

- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Recurring governance check](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [v0.82 result integration](docs/v0.82/RESULT_INTEGRATION.md)
- [v0.82 governance check](docs/v0.82/GOVERNANCE_CHECK.md)
