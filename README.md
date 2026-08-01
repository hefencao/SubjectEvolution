# SE v0.102

Reference implementation for nested-subject existence and ecological evolution simulation.

## Current direction

D1-S remains a formal environment-threshold failure because one of three seeds crossed the preregistered population floor even though all three produced structured processing division. D1-T then tested whether load, local competition, inherited danger reach and directional messages could support scout-like differentiation.

The uploaded same-seed, same-config D1-T results are backend-sensitive: the CPU run observed the complete diagnostic chain, while the GPU-hybrid run observed no same-group danger-message delivery or aligned flee response. D1-T therefore does not qualify the mechanism.

D1-U corrects the physical semantics before any further social interpretation:

- harvested resources are depleted once by the harvest commit; rival overlap is recorded as scarcity pressure, not duplicated as synthetic energy or integrity damage;
- resource signals read the post-harvest current field;
- terrain resists both grid-field signal diffusion and direct-message transport;
- CPU and accelerated runs use the same seed and config for debug comparison, without requiring identical chaotic trajectories;
- no formal environment panel, gene audit, scout role or selection claim is declared.

The local CPU debug seed completed tick 600 with corrected zero duplicate body cost, but ended at 55 alive and is not population-ready. The local auto backend fell back to CPU, so real-device verification remains outstanding.

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

## D1-U workflow

```text
se-study show studies/d1u_depletion_pressure_terrain_signal_v1
se-study run studies/d1u_depletion_pressure_terrain_signal_v1 evidence-audit
se-study run studies/d1u_depletion_pressure_terrain_signal_v1 prepare-config
se-study run studies/d1u_depletion_pressure_terrain_signal_v1 probe-cpu --dry-run
se-study run studies/d1u_depletion_pressure_terrain_signal_v1 probe-accelerated --dry-run
```

The workflow contains only physical-semantics and backend debug steps. It declares no formal social-structure panel, gene-persistence, paired, selection or candidate-ledger step.

## Validation and packaging

Run `make conda-sync` only after changing package metadata, entry points, dependencies, package structure or editable checkout location. Normal validation:

```text
make test
make conda-check
make parity-gpu
```

`make package` builds a disposable archive copy and keeps only the current v0.102 iteration note. Local history under `docs/迭代/` remains untouched.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.102 D1-U iteration](docs/迭代/v0.102_D1-U_资源耗竭竞争与地形信号传播.md)
