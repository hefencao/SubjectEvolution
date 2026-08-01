# SE v0.100

Reference implementation for nested-subject existence and ecological evolution
simulation.

## Current direction

D1-R is closed as a formal threshold failure. Its three complete seeds all
showed physical heterogeneity and real within-group raw-resource exchange, but
only seeds 97101 and 97102 reproduced at least two persistent division-candidate
groups. Seed 97103 did not, and its trajectory also passed through a deep
population bottleneck with low final founder-lineage breadth. The result does
not authorize a gene audit or social/evolutionary interpretation.

D1-S continues environment construction rather than changing genes. It keeps
the complete subject, complementary recipes, exchange rules, costs and group
diagnostics unchanged while making two shared physical changes:

- the antipodal material circuit for each resource channel becomes closer in
  strength to the primary circuit;
- all source and processing provinces are widened uniformly.

Each channel is normalized after combining both circuits, so global mean
material opportunity is unchanged. The aim is to create multiple independently
reachable material loops capable of supporting more than one structured group,
not to reward any genotype, lineage, group or role.

The formal threshold remains at least two persistent division-candidate group
lineages in every independent seed. D1-S additionally rejects runs whose
recorded population falls below half the initial population or whose final
effective founder-lineage count is below four. A group label, a single
successful seed, or a rebound of a few lineages is not environment plurality.

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

## D1-S workflow

```text
se-study show studies/d1s_replicated_material_circuits_v1
se-study run studies/d1s_replicated_material_circuits_v1 evidence-audit
se-study run studies/d1s_replicated_material_circuits_v1 prepare-config
se-study run studies/d1s_replicated_material_circuits_v1 structured-panel --dry-run
se-study run studies/d1s_replicated_material_circuits_v1 structure-summary --dry-run
```

`environment-probe` remains available only for simple parameter debugging. No
gene-persistence, paired, selection or candidate-ledger step is declared.

## Validation and packaging

Run `make conda-sync` only after changing package metadata, entry points,
dependencies, package structure or editable checkout location. Normal validation:

```text
make test
make conda-check
make parity-gpu
```

`make package` builds a disposable archive copy and keeps only the current
v0.100 iteration note. Local history under `docs/迭代/` remains untouched.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.100 D1-S iteration](docs/迭代/v0.100_D1-S_重复物质回路与瓶颈感知环境资格.md)
