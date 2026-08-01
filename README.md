# SE v0.106

Reference implementation for nested-subject existence and ecological evolution simulation.

## Current direction

D1-Y replaces the idea that one short material-return ratio can represent complete partner value. Relationship learning now has independently auditable channels and timescales:

- short-horizon material giving and receiving remain one channel;
- transferred knowledge creates a separate long-horizon channel only after the receiver later verifies its prediction against a realized five-dimensional outcome;
- material and knowledge windows settle independently rather than being collapsed into one scalar formula at event time;
- fixed SHARE trust bonuses and penalties remain disabled in the D1-Y configuration;
- knowledge quality is evidence of verified information value, not yet proof that the receiver used the information or gained a causal survival advantage.

The D1-Y debug run demonstrates multi-timescale relation semantics but does not enter Epoch 1. Population qualification, stable historical partner identity after death, protection/conflict/opportunity-cost channels, predictive validity and shared-checkpoint neutralization remain open.

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

## D1-Y workflow

```text
se-study show studies/d1y_multichannel_interest_feedback_v1
se-study run studies/d1y_multichannel_interest_feedback_v1 evidence-audit
se-study run studies/d1y_multichannel_interest_feedback_v1 prepare-config
se-study run studies/d1y_multichannel_interest_feedback_v1 relation-probe --dry-run
se-study run studies/d1y_multichannel_interest_feedback_v1 relation-summary --dry-run
```

The workflow is a single-seed semantics debug. It contains no formal Epoch 1 panel, group-rule implementation, gene audit, selection test or subjecthood claim.

## Epoch bases and regional branches

Long-horizon evolution may freeze a qualified full-world checkpoint as an immutable epoch base through `se-epoch`. Regional branch v1 preserves the complete environment coordinate frame and fields while pruning active entities and cross-boundary social state. It is an explicit intervention, not an unbiased miniature world.

## Validation and packaging

Run `make conda-sync` only after changing package metadata, entry points, dependencies, package structure or editable checkout location. Normal validation:

```text
make test
make conda-check
make parity-gpu
```

`make package` builds a disposable archive copy and keeps only the current v0.106 iteration note. Local history under `docs/迭代/` remains untouched.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.106 D1-Y iteration](docs/迭代/v0.106_D1-Y_多时程多通道利益反馈与知识价值归因.md)
