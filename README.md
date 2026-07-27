# SE v0.40

`SE` 是围绕多维环境、可遗传分化、动态知识与候选主体结构构建的可审计演化模拟参考实现。

## Conda 本地工作流

本地不再为每次源码修改重新安装 wheel。激活目标 conda 环境后，对当前 checkout 做一次 editable 安装：

```bash
conda activate <your-env>
make conda-sync
```

普通源码修改会立即生效。仅在修改 `pyproject.toml`、console scripts、依赖、版本或移动项目目录后重新执行 `make conda-sync`。

日常测试：

```bash
make test
```

长跑或交付前：

```bash
make conda-check
```

`conda-check` 会确认当前 Python 属于 `CONDA_PREFIX`、`se` 来自该 checkout、安装为 editable、五个入口与 metadata 一致，并在源码树外执行 smoke。不要在正常运行时再设置 `PYTHONPATH=src`。

Wheel/sdist 仍可用作发布产物，但 `make release-check` 只审计产物，不是本地运行环境。

## 主要运行入口

```bash
se --config <CONFIG> --seed 10001 --output <DIR> --backend cpu
```

```bash
se-multi \
  --config configs/mvp_short_d2a_contextual_harvest_longrun.json \
  --seeds 10001,10002,10003 \
  --checkpoint-ticks 2400,2640,2760,2820,2880,3000 \
  --until-tick 3000 \
  --output runs/d2a_contextual_modules_multiseed \
  --backend gpu
```

## D1 因子实验

```bash
se-d1-factorial \
  --run-dir runs/d1c_multiseed/seed_10001 \
  --run-dir runs/d1c_multiseed/seed_10002 \
  --run-dir runs/d1c_multiseed/seed_10003 \
  --output analyses/d1_factorial \
  --phases peak,trough \
  --horizon 120 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

## D2-B 模块贡献审计

3000-tick D2-A 结果显示模块广泛表达，但最终残差很小，同时有效谱系和策略维度明显下降。因此 v0.40 不增加模块复制或新端口，而是先区分结构表达与因果贡献。

```bash
se-d2-audit \
  --run-dir runs/d2a_contextual_modules_multiseed/seed_10001 \
  --run-dir runs/d2a_contextual_modules_multiseed/seed_10002 \
  --run-dir runs/d2a_contextual_modules_multiseed/seed_10003 \
  --output analyses/d2b_module_audit \
  --phases peak,trough \
  --horizon 120 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

每个 checkpoint 运行：baseline、全模块中和和四个逐模块中和分支，并报告单模块效应、总模块效应、非加性和取消程度。

## 当前科学主线

1. **D0：** 四资源具有独立外生空间、时间与扩散过程。
2. **D1-A：** 工作记忆、知识、关系与注意力容量可独立遗传、计费和消融。
3. **D1-B：** 固定采集预算下，由遗传 affinity 采样单一资源通道。
4. **D1-C：** 请求流与实现流分离；共享 checkpoint 的 affinity × capacity 因子实验。
5. **D2-A：** 四个表达门控上下文模块发布有限零和采集权重残差。
6. **D2-B：** 独立模块贡献诊断与共享 checkpoint 的 leave-one-module-out 因果审计。

模块复制、删除、任意重联和新物理端口继续阻塞，直到 D2-B 在多个 seed/phase 中识别出可重复、非纯成本的模块效应。

## 文档

- [项目立项](docs/PROJECT_CHARTER.md)
- [架构与提交边界](docs/ARCHITECTURE.md)
- [项目状态](docs/PROJECT_STATUS.md)
- [科学问题](docs/SCIENTIFIC_ISSUES.md)
- [Conda editable 工作流](docs/v0.40/CONDA_EDITABLE_WORKFLOW.md)
- [D2-A 3000-tick 结果评估](docs/v0.40/INPUT_D2A_LONG_RUN_ASSESSMENT.md)
- [D2-B 模块贡献审计](docs/v0.40/D2B_MODULE_CONTRIBUTION_AUDIT.md)
- [D2-B smoke](docs/v0.40/D2B_PAIRED_SMOKE_REPORT.md)
- [下一轮配对计划](docs/v0.40/LONG_RUN_PLAN.md)
