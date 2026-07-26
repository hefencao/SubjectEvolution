# Subject Evolution v0.25

一个以**可审计世界状态、局部交互、遗传策略、动态知识副本和候选主体结构**为核心的演化模拟参考实现。

当前科学基线不引入第二套“生物型危险实体”。环境层只包含资源、权威危险场、死亡痕迹及默认关闭的低耦合标量场插件；具有出生、死亡、策略、关系、记忆或谱系的危险主体，应由现有实体系统分化，而不是在环境模块中复制。

## v0.25 重点

v0.25 不修改世界规则，而是把 v0.24 的自然事件 manifest 推进为可执行实验工作流：

- 从已签名 manifest 构造独立的执行计划，不重新选择锚点；
- 支持 `OLD=NEW` 路径前缀映射，解决 manifest 中绝对路径跨机器迁移问题；
- 执行前校验 progress、resolved config 与 checkpoint 的 SHA-256；
- 相同 checkpoint、相同 intervention 的多个锚点共享一条最长轨迹；
- 每条轨迹写完成标记，可安全断点续跑；
- 结果先在 seed 内平均，再跨 seed 汇总方向，避免把同一 seed 的多个锚点当作独立重复；
- 压缩包不再包含 `docs/archive`，根目录只保留稳定入口文件；
- `pyproject.toml` 采用项目提供的配置，构建依赖中移除显式 `wheel`。

## 安装

```bash
python -m venv .venv
source .venv/bin/activate            # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

CPU 参考实现只需要 NumPy。GPU 路径需要与本机 CUDA 主版本匹配的 CuPy；CUDA 12 和 CUDA 13 的 CuPy 包不能同时安装。

## 快速运行

```bash
python -m subject_evolution.cli \
  --config configs/smoke_cpu.json \
  --output runs/smoke_cpu \
  --backend cpu
```

旗舰科学长跑配置：

```bash
python -m subject_evolution.multi_seed \
  --config configs/mvp_short_latent_l2_memory_topk_inherited_heterogeneous_budget_matched_costed_transfer_mortality_trace_adaptive_groups_longrun.json \
  --seeds 10001,10002,10003 \
  --output runs/mortality_trace_adaptive_groups_multiseed \
  --backend gpu \
  --until-tick 1500
```

该配置使用 `gpu_semantics_mode="strict-reference"`。请求 GPU 时会验证设备，但世界语义仍由 CPU reference 路径权威执行；真实 `hybrid-accelerated` 多 tick parity 尚未证明，不能作为科学基线。

## 生成暴露盲选 manifest

```bash
python -m subject_evolution.natural_event_matrix \
  --run-root runs/mortality_trace_adaptive_groups_multiseed \
  --analysis-json analyses/mortality_trace_adaptive_groups/long_run_analysis.json \
  --event-kinds scarcity,crowding,mortality \
  --event-quantile 0.80 \
  --events-per-kind 2 \
  --horizon 120 \
  --output analyses/natural_event_matrix
```

锚点选择只读取 tick、区域 alive、稀缺、拥挤、死亡压力和 checkpoint 可用性；凝聚度、传播流、文化根、谱系和动作结果均被排除。

## v0.25 预检与执行 manifest

先只生成执行计划和预检报告：

```bash
python -m subject_evolution.natural_event_execution \
  --manifest analyses/natural_event_matrix/natural_event_matrix_manifest.json \
  --output analyses/natural_event_execution \
  --path-prefix /旧项目绝对路径=/当前项目绝对路径
```

检查：

```text
natural_event_execution_plan.json
natural_event_execution_plan.md
natural_event_execution_preflight.json
```

预检通过后执行：

```bash
python -m subject_evolution.natural_event_execution \
  --manifest analyses/natural_event_matrix/natural_event_matrix_manifest.json \
  --output analyses/natural_event_execution \
  --path-prefix /旧项目绝对路径=/当前项目绝对路径 \
  --execute \
  --backend cpu
```

默认要求 progress、resolved config 和 checkpoint 全部通过哈希审计。仅在已独立保存并验证 manifest、但原 progress/config 不再可用时，才使用：

```text
--checkpoint-only-preflight
```

已完成轨迹会通过 `natural_event_trajectory.json` 识别并复用。存在不完整目录时默认拒绝覆盖；明确重跑使用 `--overwrite-existing`。

可按 seed、事件、锚点或 intervention 分批执行：

```bash
--seeds 10001,10002
--event-kinds crowding,mortality
--anchor-id seed_10001-crowding-r14-t270
--interventions disable-knowledge-transfer,freeze-group-refresh
```

每个 intervention 与 baseline 仍从同一个事件前 `.sechk` 出发并使用相同 keyed randomness。自然事件不是随机分配，因此结果识别的是给定锚点后的短期机制消融效应，不是环境暴露本身的随机试验效应。

## checkpoint 与单项重放

```bash
python -m subject_evolution.replay \
  --checkpoint runs/example/checkpoint_00000600.sechk \
  --output runs/transfer_off \
  --until-tick 720 \
  --intervention disable-knowledge-transfer \
  --backend cpu
```

`.sechk` 使用 pickle 载荷，只能加载本项目生成且来源可信的 checkpoint。

## 核心能力

- 2D 周期世界、四类不可完全替代资源、异步多生态位季节变化；
- 固定容量 SoA 实体、出生/死亡计划、谱系继承与稀疏突变；
- 可遗传 8-action × 16-feature 策略矩阵；
- K1–K4 动态知识副本、局部后果更新、有代价传播、内容根谱系与候选图；
- L1/L2 可变长度潜知识、量化 MLP residual、路由计算成本；
- 量化工作记忆与遗传 Top-k 临时选择器；
- 固定预算四资源亲和、死亡痕迹观察、adaptive group refresh；
- CPU reference、GPU strict-reference 和实验性 hybrid-accelerated 路径；
- 完整 checkpoint、共同前史分支、相位/局部事件配对反事实；
- 长期遗传、群组、局部压力和文化传播诊断。

## 文档

- [当前项目状态](docs/PROJECT_STATUS.md)
- [科学问题与研究债务](docs/SCIENTIFIC_ISSUES.md)
- [变更记录](docs/CHANGELOG.md)
- [架构与提交边界](docs/ARCHITECTURE.md)
- [v0.24 文档](docs/v0.24/README.md)
- [v0.25 文档与验证](docs/v0.25/README.md)

发行压缩包不包含 `docs/archive`。更早的完整历史仍保存在旧版本发行包中。
