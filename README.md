# SE v0.107

Reference implementation for nested-subject existence and ecological evolution simulation.

## Current direction

Version 0.107 freezes the design for the next subject-formation substrate without changing runtime behavior.

The project will use a **partitioned unified subject graph**:

- one evolvable node/edge identity space;
- initially biased fast sensorimotor, persistent-state, delayed-association and integrative-drive regions;
- shared activation routing and later delayed-plasticity routing on the same graph;
- explicit structural, execution, memory, bandwidth and plasticity costs;
- no built-in trust, benefit, friend, enemy, knowledge-value or social-role semantics.

The project may preset general cognitive architecture to reduce evolutionary search time. It must not preset concrete cognition. D1-X/Y are retained as fixed-cognition comparison baselines and engineering fixtures, not extended as the primary subject model.

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

The pointer lives in ignored `.se-workspace.toml` and does not affect protocol identity or release artifacts.

## Implementation starting point

The next implementation release is restricted to Stage 1 of the frozen contract: disabled-by-default Subject Graph VM configuration and inert fixed-capacity storage, including checkpoint and lifecycle handling. It must not yet influence action policy or add a subjective reward.

See:

- [Partitioned Subject Graph VM v1](docs/PARTITIONED_SUBJECT_GRAPH_VM.md)
- [Machine-readable architecture contract](protocols/epochs/subject_graph_vm_v1.json)
- [Epoch 1 functional qualification v2](protocols/epochs/entity_subject_functional_qualification_v2.json)
- [Primary-direction decision](protocols/decisions/subject_graph_vm_direction_v1.md)

## Epoch bases and regional branches

Long-horizon evolution may freeze a qualified full-world checkpoint as an immutable epoch base through `se-epoch`. Regional branch v1 preserves the complete environment coordinate frame and fields while pruning active entities and cross-boundary social state. It is an explicit intervention, not an unbiased miniature world.

## Validation and packaging

Run `make conda-sync` after changing package metadata, entry points, dependencies, package structure or editable checkout location. Normal validation:

```text
make test
make conda-check
make parity-gpu
```

`make package` builds a disposable archive copy and keeps only the current v0.107 iteration note. Local history under `docs/迭代/` remains untouched.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Partitioned Subject Graph VM](docs/PARTITIONED_SUBJECT_GRAPH_VM.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.107 D1-Z iteration](docs/迭代/v0.107_D1-Z_分区统一主体图实现准备.md)
