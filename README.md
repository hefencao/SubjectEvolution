# Subject Evolution v0.26

一个以**可审计世界状态、局部交互、遗传策略、动态知识副本和候选主体结构**为核心的演化模拟参考实现。

当前科学基线不引入第二套“生物型危险实体”。环境层只包含资源、权威危险场、死亡痕迹及默认关闭的低耦合标量场插件；具有出生、死亡、策略、关系、记忆或谱系的危险主体，应由现有实体系统分化，而不是在环境模块中复制。

## v0.26 重点

v0.26 不修改世界规则，主要解决 natural-event 配对实验中的**结果解释与共同测量边界**：

- 从同一 checkpoint 冻结稳定实体 ID 与群组 token，形成 diagnostic-only common boundary；
- 分享流同时按分支当前标签和 checkpoint-common 标签记账；
- 槽位复用不会让新生实体继承旧群组身份；
- natural-event results v3 分离 current-label cohesion、common-boundary cohesion 和 boundary-definition gap；
- 新增结果审计器，区分 manipulation check、文化机制近端指标、测量耦合指标和下游区域状态；
- 支持读取 v0.25 results v2 与 execution plan v1，并生成 v0.26 后续执行计划；
- 发行包继续不包含 `docs/archive`，`pyproject.toml` 保持无显式 `wheel` 构建依赖。

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

## 自然事件实验工作流

### 1. 生成暴露盲选 manifest

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

### 2. 预检与执行

```bash
python -m subject_evolution.natural_event_execution \
  --manifest analyses/natural_event_matrix/natural_event_matrix_manifest.json \
  --output analyses/natural_event_execution \
  --path-prefix /旧项目绝对路径=/当前项目绝对路径
```

预检通过后增加：

```text
--execute --backend gpu --gpu-semantics-mode strict-reference
```

v0.26 默认启用 checkpoint-common boundary audit。若只为历史兼容而明确不需要该诊断，可使用：

```text
--no-common-boundary-audit
```

旧 v0.25 trajectory marker 不会被误复用为带共同边界的 v0.26 轨迹；共同边界复跑应使用新输出目录，或明确 `--overwrite-existing`。

### 3. 审计结果并生成后续计划

```bash
python -m subject_evolution.natural_event_result_audit \
  --results analyses/natural_event_execution/natural_event_matrix_results.json \
  --execution-plan analyses/natural_event_execution/natural_event_execution_plan.json \
  --manifest analyses/natural_event_matrix/natural_event_matrix_manifest.json \
  --output analyses/natural_event_result_audit
```

审计器不会重选锚点或执行分支。它验证哈希链、标注结果的解释层级，并可生成：共同边界复跑、剩余事件复制和剩余机制消融计划。

生成的签名计划可直接执行：

```bash
python -m subject_evolution.natural_event_execution \
  --execution-plan analyses/natural_event_result_audit/common_boundary_rerun_execution_plan.json \
  --output analyses/common_boundary_rerun \
  --execute --backend gpu --gpu-semantics-mode strict-reference
```

使用 `--execution-plan` 时不能再附加路径、锚点、事件或 intervention 过滤；若需修改，必须从原 manifest 重建并产生新的计划哈希。

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
- 长期遗传、群组、局部压力和文化传播诊断；
- 暴露盲选 manifest、哈希预检、共享轨迹、断点续跑、共同边界评估与结果审计。

## 文档

- [当前项目状态](docs/PROJECT_STATUS.md)
- [科学问题与研究债务](docs/SCIENTIFIC_ISSUES.md)
- [变更记录](docs/CHANGELOG.md)
- [架构与提交边界](docs/ARCHITECTURE.md)
- [v0.24 文档](docs/v0.24/README.md)
- [v0.25 文档](docs/v0.25/README.md)
- [v0.26 文档与结果审计](docs/v0.26/README.md)

发行压缩包不包含 `docs/archive`。更早的完整历史仍保存在旧版本发行包中。
