# Subject Evolution v0.27

一个以**可审计世界状态、局部交互、遗传策略、动态知识副本和候选主体结构**为核心的演化模拟参考实现。

科学核心继续不引入第二套“生物型危险实体”。环境层只包含资源、权威危险场、死亡痕迹及默认关闭的低耦合标量场插件；具有出生、死亡、策略、关系、记忆或谱系的危险主体，应由现有实体系统分化，而不是在环境模块中复制。

## v0.27 重点

v0.27 不改变世界动力学，主要补齐自然事件配对实验的两个诊断缺口：

- 新增 stable-ID **event cohort endpoint decomposition**，把区域终点人口变化精确拆为：事件 cohort 留在区域、存活但迁出、死亡/终点缺失、事件时已存在实体迁入、事件后出生且终点仍在区域；
- 分解恒等式逐 anchor 验证，残差必须为 0；该诊断不反馈策略、行动、关系、群组、生命周期或环境；
- natural-event execution plan 升级为 v3，trajectory marker 升级为 v3，paired results 升级为 v4；
- 新增 `subject_evolution.natural_event_result_synthesis`，可合并多个签名结果集、优先采用诊断更完整的重复分支、重新执行 seed-first 聚合，并检查 manifest 覆盖率；
- 对用户提供的 4 份结果完成综合：18 anchors、72/108 eligible pairs；关闭传播对局部文化根的负向作用在 crowding、mortality、scarcity 三类事件中重复；冻结群组刷新造成的 current-label cohesion 下降主要由边界定义变化解释；
- 自动生成三份 v3 cohort 复跑计划，覆盖当前主要机制和尚未执行的 scarcity/mortality 知识消融；
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

v0.27 默认同时启用：

- checkpoint-common group boundary audit；
- stable-ID event cohort endpoint audit。

仅为历史兼容而明确关闭时可使用：

```text
--no-common-boundary-audit
--no-event-cohort-audit
```

旧 marker 不会被静默复用为带新诊断的轨迹。

### 3. 综合多个结果集

```bash
python -m subject_evolution.natural_event_result_synthesis \
  --results analyses/initial_crowding/natural_event_matrix_results.json \
  --results analyses/common_boundary_rerun \
  --results analyses/remaining_event_replication \
  --results analyses/remaining_mechanism_ablation \
  --manifest analyses/natural_event_matrix/natural_event_matrix_manifest.json \
  --output analyses/natural_event_result_synthesis
```

目录参数会递归发现 `natural_event_matrix_results.json`。综合器按 `(anchor_id, intervention)` 合并，重复分支必须在世界结果字段上兼容；若同一分支存在共同边界或 cohort 诊断更完整的版本，会优先使用更完整版本。

### 4. 执行已签名 follow-up plan

```bash
python -m subject_evolution.natural_event_execution \
  --execution-plan analyses/natural_event_result_synthesis/primary_event_cohort_rerun_execution_plan.json \
  --output analyses/primary_event_cohort_rerun \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

使用 `--execution-plan` 时不能再附加路径、锚点、事件、diagnostic 或 intervention 过滤；若需修改，必须从原 manifest 重建并产生新的计划哈希。

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
- 暴露盲选 manifest、哈希预检、共享轨迹、断点续跑、共同边界、event cohort 分解与跨结果综合。

## 文档

- [当前项目状态](docs/PROJECT_STATUS.md)
- [科学问题与研究债务](docs/SCIENTIFIC_ISSUES.md)
- [变更记录](docs/CHANGELOG.md)
- [架构与提交边界](docs/ARCHITECTURE.md)
- [v0.24 文档](docs/v0.24/README.md)
- [v0.25 文档](docs/v0.25/README.md)
- [v0.26 文档](docs/v0.26/README.md)
- [v0.27 文档与结果综合](docs/v0.27/README.md)

发行压缩包不包含 `docs/archive`。更早的完整历史仍保存在旧版本发行包中。
