# SE v0.94

Reference implementation for nested-subject existence and ecological evolution
simulation.

## Current direction

D1-N is now formally qualified: seeds 93101--93103 all completed tick 480 under
one canonical `source-health-contract-v2`, passed every required-final condition,
and triggered no warning or catastrophic hard-stop. This establishes a healthy
multi-generation turnover substrate, but not an evolutionary result.

v0.94 adds D1-O, the capability-affordability and maturation boundary. The
qualified D1-N configuration is frozen as compact evidence. A conservative
per-capita cost budget is derived from the weakest formal source, and exactly one
existing inherited interface is attached: morphology gene 6 selects a bounded,
conservative parent-to-newborn endowment. The four levels average to the fixed
0.9 substrate endowment, so the random initial population receives no mean event-
debit increase. Paired commands are intentionally absent until the attached-
capability source re-passes the unchanged health gate.

## Workspace layout

- [`studies/`](studies/README.md): study design, protocols, declarative workflows, and frozen evidence.
- [`runs/`](runs/README.md): source trajectories, intervention branches, and checkpoints.
- [`analyses/`](analyses/README.md): derived results and compact reports.
- [`state/`](state/README.md): mutable local decision overlays and generated configs.
- [`protocols/`](protocols/README.md): project-wide registries and immutable release decisions.
- [`configs/`](configs/README.md): reusable project-level configuration presets.

## Configure external result storage

Compact result archives must not be written into the project tree. Configure one
project-local pointer after editable installation:

```text
mkdir -p ../SubjectEvolution-results
se-study config --set-result-dir ../SubjectEvolution-results
se-study config
```

The setting is stored in ignored `.se-workspace.toml`; it does not enter release
artifacts or scientific protocol identity.

## D1-O workflow

```text
se-study show studies/d1o_budgeted_offspring_investment_v1
se-study run studies/d1o_budgeted_offspring_investment_v1 budget-check --dry-run
se-study run studies/d1o_budgeted_offspring_investment_v1 prepare-config --dry-run
```

Every workflow parameter is declared and can be overridden explicitly. The
resolved argv is printed before execution, undeclared parameters are rejected,
and no shell is used.

## Validation and packaging

Use `make conda-sync` only after changing version metadata, entry points,
dependencies, package structure, or the editable checkout location. Normal
validation remains:

```text
make test
make conda-check
make parity-gpu
```

`make package` builds a disposable archive copy, removes old iteration notes only
from that copy, and keeps the current v0.94 note. Local history under `docs/迭代/`
is never inspected or deleted by version consistency or `conda-sync`.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.94 D1-O iteration](docs/迭代/v0.94_D1-O_能力接入预算与有界后代投入.md)
