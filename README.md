# Subject Evolution v0.28

一个以**可审计世界状态、局部交互、遗传策略、动态知识副本和候选主体结构**为核心的演化模拟参考实现。

科学核心不引入第二套“生物型危险实体”。环境层只包含资源、权威危险场、死亡痕迹及默认关闭的低耦合标量场插件；具有出生、死亡、策略、关系、记忆或谱系的危险主体，应由现有实体系统分化，而不是在环境模块中复制。

## v0.28 重点

v0.28 不修改默认世界动力学，修正自然事件配对实验的**干预时序与共同 cohort 证明**：

- 审计用户提供的 v0.27 cohort 结果后发现，72/72 个已执行 pairs 都在 prior checkpoint 就应用干预，比名义 event tick 提前 30 或 60 ticks；
- 48/72 pairs 在 event tick 的区域 alive 已不同，其余 pairs 也没有 stable-ID 集合哈希，不能证明是同一事件 cohort；
- 新增 `subject_evolution.natural_event_timed_execution`：共同前史只重放一次到 event tick，再从同一个 event checkpoint 分出 baseline/interventions；
- event cohort schema 升级为 v2，发布全局和区域 stable-ID SHA-256；每个 pair 必须通过 alive、全局身份、区域身份三项 pairing audit；
- 旧 `natural_event_execution` 继续保留，明确标记 `checkpoint-immediate-v1`，用于研究机制从 prior checkpoint 开始后的总效应；
- result synthesis 升级为 v2，禁止混合不同 intervention timing estimand，并自动生成三份 event-timed signed plans；
- 发行包继续排除 `docs/archive`，`pyproject.toml` 保持无显式 `wheel` 构建依赖。

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

### 2. Event-timed 计划与预检

推荐的 post-event 估计量使用：

```bash
python -m subject_evolution.natural_event_timed_execution \
  --manifest analyses/natural_event_matrix/natural_event_matrix_manifest.json \
  --event-kinds crowding,mortality,scarcity \
  --interventions disable-knowledge-transfer,freeze-group-refresh,neutralize-resource-affinity \
  --output analyses/event_timed_primary \
  --path-prefix /旧项目绝对路径=/当前项目绝对路径
```

该计划先从签名 checkpoint 只演进一次到 event tick，保存 event checkpoint，然后才分出 baseline 与 intervention。预检通过后执行：

```bash
python -m subject_evolution.natural_event_timed_execution \
  --execution-plan analyses/event_timed_primary/natural_event_timed_execution_plan.json \
  --output analyses/event_timed_primary \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

每个 pair 都必须证明：

```text
event alive count equal
event global stable-ID hash equal
event regional stable-ID hash equal
```

### 3. Checkpoint-immediate 历史估计量

旧入口仍可用于“从 prior checkpoint 开始改变机制”的实验：

```bash
python -m subject_evolution.natural_event_execution \
  --manifest analyses/natural_event_matrix/natural_event_matrix_manifest.json \
  --output analyses/checkpoint_immediate
```

其结果明确标记 `intervention_timing="checkpoint-immediate-v1"`。它可能改变名义事件暴露和事件 cohort，不应与 event-timed 结果合并。

### 4. 综合多个结果集

```bash
python -m subject_evolution.natural_event_result_synthesis \
  --results analyses/result_batch_a \
  --results analyses/result_batch_b \
  --manifest analyses/natural_event_matrix/natural_event_matrix_manifest.json \
  --output analyses/natural_event_result_synthesis
```

综合器按 `(anchor_id, intervention)` 合并，先 seed 内平均再跨 seed 汇总，并拒绝混合 `checkpoint-immediate-v1` 与 `anchor-event-tick-v1` 两种估计量。

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
- 暴露盲选 manifest、哈希预检、断点续跑、共同边界、stable-ID cohort、event-timed pairing 与跨结果综合。

## 文档

- [当前项目状态](docs/PROJECT_STATUS.md)
- [科学问题与研究债务](docs/SCIENTIFIC_ISSUES.md)
- [变更记录](docs/CHANGELOG.md)
- [架构与提交边界](docs/ARCHITECTURE.md)
- [v0.24 文档](docs/v0.24/README.md)
- [v0.25 文档](docs/v0.25/README.md)
- [v0.26 文档](docs/v0.26/README.md)
- [v0.27 文档](docs/v0.27/README.md)
- [v0.28 文档与 event-timed 计划](docs/v0.28/README.md)

发行压缩包不包含 `docs/archive`。更早的完整历史仍保存在旧版本发行包中。
