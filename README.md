# SE v0.95

Reference implementation for nested-subject existence and ecological evolution
simulation.

## Current direction

D1-N qualified a healthy multi-generation turnover substrate. D1-O then showed
that the inherited conservative offspring-investment interface preserves that
substrate on all three independent seeds 94101--94103.

v0.95 corrects the iteration strategy. The qualified source is not a one-gene
organism: it already contains 704 inherited coordinates spanning morphology,
action policy, knowledge routing, memory, sparse selection, capacities,
functional modules and physiology. Its environment already contains four
asynchronous resource fields with distinct body effects, plus oxygen, terrain,
wear and mortality-trace structure.

D1-P therefore stops adding and auditing one isolated gene at a time. It freezes
the whole qualified subject-environment system as one integrated baseline, runs
a bounded independent multi-generation panel, and screens which inherited
coordinates or blocks remain present, concentrate, thin or disappear. Only
repeated cross-seed problems with matching expression/use or physical evidence
may motivate later adjustment.

## Workspace layout

- [`studies/`](studies/README.md): study design, protocols, workflows and frozen evidence.
- [`runs/`](runs/README.md): runtime trajectories and checkpoints.
- [`analyses/`](analyses/README.md): derived reports, including compact persistence scans.
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

## D1-P workflow

```text
se-study show studies/d1p_integrated_ecological_subject_v1
se-study run studies/d1p_integrated_ecological_subject_v1 baseline-check --dry-run
se-study run studies/d1p_integrated_ecological_subject_v1 prepare-config --dry-run
se-study run studies/d1p_integrated_ecological_subject_v1 integrated-panel --dry-run
```

No paired or per-gene effect command is declared in D1-P.

## Validation and packaging

Run `make conda-sync` only after changing package metadata, entry points,
dependencies, package structure or editable checkout location. Normal validation:

```text
make test
make conda-check
make parity-gpu
```

`make package` builds a disposable archive copy and keeps only the current v0.95
iteration note. Local history under `docs/迭代/` remains untouched.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.95 D1-P iteration](docs/迭代/v0.95_D1-P_多元生态主体与基因存续扫描.md)
