# SE v0.101

Reference implementation for nested-subject existence and ecological evolution
simulation.

## Current direction

D1-S is closed as a formal threshold failure. All three seeds completed tick
1800 and reproduced physical heterogeneity, real within-group raw-resource
exchange and multiple persistent processing-division groups. Seed 100101,
however, fell to 47 alive from 128 initial and failed the preregistered 0.50
population-substrate floor. The result does not authorize gene or social-role
interpretation.

D1-T addresses a separate mechanism gap behind the absence of scout-like
specialization. The previous world had no rival resource contest, no carrying
burden, no inherited danger reach, and no directional use for danger messages.
The opt-in D1-T chain adds role-neutral load costs, symmetric local harvest
contest, shared inherited danger sensing, contest-bearing signals and FLEE
movement away from a direct-message source. It adds no scout label, attack
profession, reward or gene.

A preregistered single debug seed completed tick 900 with a healthy population
and observed the complete pressure-information-response chain, but produced no
persistent reconnaissance-candidate lineage. This shows the missing physical
interfaces were more important than merely adding ticks or groups. The result
is mechanism-debug evidence only; environment qualification and all gene,
selection and role claims remain blocked.

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

## D1-T workflow

```text
se-study show studies/d1t_reconnaissance_pressure_chain_v1
se-study run studies/d1t_reconnaissance_pressure_chain_v1 evidence-audit
se-study run studies/d1t_reconnaissance_pressure_chain_v1 prepare-config
se-study run studies/d1t_reconnaissance_pressure_chain_v1 mechanism-probe --dry-run
se-study run studies/d1t_reconnaissance_pressure_chain_v1 mechanism-summary --dry-run
```

The only runtime step is a single-seed mechanism probe. No formal social-structure panel, gene-persistence, paired, selection or candidate-ledger step is declared.

## Validation and packaging

Run `make conda-sync` only after changing package metadata, entry points,
dependencies, package structure or editable checkout location. Normal validation:

```text
make test
make conda-check
make parity-gpu
```

`make package` builds a disposable archive copy and keeps only the current
v0.101 iteration note. Local history under `docs/迭代/` remains untouched.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.101 D1-T iteration](docs/迭代/v0.101_D1-T_对抗负重与侦察信息价值链.md)
