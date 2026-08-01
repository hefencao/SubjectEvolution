# SE v0.97

Reference implementation for nested-subject existence and ecological evolution
simulation.

## Current direction

D1-Q is closed as a failed formal environment/demographic construction: the
reported three-seed panel produced no passing seed. Its former executable
genetic-retention steps have been removed. The project is not authorized to
interpret coordinate thinning, run a one-round gene audit, or attach another
isolated gene/environment pair.

D1-R first constructs an environment capable of producing structured dependence:

- four separated and periodically forced raw-resource source provinces;
- processing provinces displaced from source provinces;
- complementary recipes that each require at least two raw channels;
- bounded role-neutral raw-resource exchange;
- exchange-supported social relations;
- observational tracking of stable within-group harvesting, processing,
  transport/exchange and coordination differences.

A `group` label is not evidence of social structure. The minimum formal
environment threshold is three viable independent seeds in which physical
heterogeneity, real group-internal material exchange, and at least two persistent
within-group division candidates are reproduced. This threshold still does not
authorize gene analysis, adaptation or selection claims.

The frozen D1-R seed 97011 is exploratory parameter-debug evidence only. It
retains 91 entities at tick 600, produces five detected groups and one persistent
division-candidate group lineage. It proves the new physical/exchange paths are
active, but it does **not** pass the multiple-structured-group threshold.

## Workspace layout

- [`studies/`](studies/README.md): study design, protocols, workflows and frozen evidence.
- [`runs/`](runs/README.md): runtime trajectories and explicit replay checkpoints.
- [`analyses/`](analyses/README.md): derived reports.
- [`state/`](state/README.md): ignored generated configs and local overlays.
- [`protocols/`](protocols/README.md): project-wide registries and release decisions.
- [`configs/`](configs/README.md): reusable presets.

## Configure external result storage

```text
mkdir -p ../SubjectEvolution-results
se-study config --set-result-dir ../SubjectEvolution-results
se-study config
```

The pointer lives in ignored `.se-workspace.toml` and does not affect protocol
identity or release artifacts.

## D1-R workflow

```text
se-study show studies/d1r_structured_environment_division_v1
se-study run studies/d1r_structured_environment_division_v1 prepare-config --dry-run
se-study run studies/d1r_structured_environment_division_v1 environment-probe --dry-run
se-study run studies/d1r_structured_environment_division_v1 probe-summary --dry-run
se-study run studies/d1r_structured_environment_division_v1 structured-panel --dry-run
se-study run studies/d1r_structured_environment_division_v1 structure-summary --dry-run
```

`environment-probe` is the only single-seed step and is restricted to parameter
debugging. No gene-persistence, paired or candidate-ledger step is declared.

## Validation and packaging

Run `make conda-sync` only after changing package metadata, entry points,
dependencies, package structure or editable checkout location. Normal validation:

```text
make test
make conda-check
make parity-gpu
```

`make package` builds a disposable archive copy and keeps only the current v0.97
iteration note. Local history under `docs/迭代/` remains untouched.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.97 D1-R iteration](docs/迭代/v0.97_D1-R_结构化资源网络与群体内分工基础.md)
