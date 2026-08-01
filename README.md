# SE v0.103

Reference implementation for nested-subject existence and ecological evolution simulation.

## Current direction

D1-U corrected depletion competition and signal accounting. The supplied same-seed CPU and GPU-hybrid debug bundle now shows that both backends execute those corrected semantics, but both populations finish near 55 and therefore do not qualify an environment or social-role claim.

D1-V addresses a separate physical modelling error: movement resistance and signal transport no longer share one mandatory terrain axis.

- `terrain` remains the movement-resistance field used by locomotion and movement energy;
- `signal_openness` is an independent communication-medium field used by grid signals and direct messages;
- their spatial correlation may be positive, negative or near zero;
- a hard-to-traverse elevated region can therefore be signal-open, while an easy corridor can be signal-occluded;
- old configurations retain exact disabled-default behaviour and frozen protocol identity.

Direct conflict is assessed but not enabled. A future first implementation should be an explicit, low-lethality, default-disabled `INTERFERE` action with target, range, cost, failure and bounded physical outcome. Natural resource depletion remains competition and must not silently become body damage.

D1-V is transport-semantics debug only. It declares no formal environment panel, direct-conflict run, gene audit, scout role, selection or adaptation claim.

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

## D1-V workflow

```text
se-study show studies/d1v_independent_signal_medium_v1
se-study run studies/d1v_independent_signal_medium_v1 evidence-audit
se-study run studies/d1v_independent_signal_medium_v1 prepare-config
se-study run studies/d1v_independent_signal_medium_v1 transport-probe --dry-run
se-study run studies/d1v_independent_signal_medium_v1 transport-summary --dry-run
```

The workflow contains one CPU transport-semantics probe. It has no conflict, formal panel, gene-persistence, paired, selection or candidate-ledger step.

## Validation and packaging

Run `make conda-sync` only after changing package metadata, entry points, dependencies, package structure or editable checkout location. Normal validation:

```text
make test
make conda-check
make parity-gpu
```

`make package` builds a disposable archive copy and keeps only the current v0.103 iteration note. Local history under `docs/迭代/` remains untouched.

## Current documents

- [Project charter](docs/PROJECT_CHARTER.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Governance principles](docs/PROJECT_GOVERNANCE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Changelog](docs/CHANGELOG.md)
- [v0.103 D1-V iteration](docs/迭代/v0.103_D1-V_独立信号介质与直接冲突接入边界.md)

## 纪元基线与区域分支

长期演化达到预注册主体形成门后，可通过 `se-epoch` 将完整 checkpoint、qualification、epoch registry 与哈希锁冻结为下一纪元基线。区域分支 v1 保留完整环境场，只裁剪活跃实体和跨边界社会状态。

具体参数和执行顺序由 `studies/d1w_epoch_base_regional_branch_v1/workflow.toml` 与 `se-epoch --help` 提供，根 README 不复制命令。该分支是局部机制开发用 intervention，不是完整世界的无偏缩小版。
