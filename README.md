# Subject Evolution v0.24

一个以**可审计世界状态、局部交互、遗传策略、动态知识副本和候选主体结构**为核心的演化模拟参考实现。

当前科学基线不引入第二套“生物型危险实体”。环境层只包含资源、权威危险场、死亡痕迹及默认关闭的低耦合标量场插件；具有出生、死亡、策略、关系、记忆或谱系的危险主体，应由现有实体系统分化，而不是在环境模块中复制。

## 当前版本重点

v0.24 在 v0.23 环境插件边界之上新增：

- 跨 seed 的自然局部事件锚点规划；
- 暴露盲选：只使用稀缺、拥挤、死亡压力、区域存活量和 checkpoint 可用性选择事件；
- 带 SHA-256 的预注册 paired-intervention manifest；
- 每个锚点逐项判断 transfer、知识策略、工作记忆、Top-k、资源亲和、danger evidence 与群组刷新消融是否可识别；
- `freeze-group-refresh` 科学干预：保持已有群组标签，不再刷新，新生体保持未分组、死亡体正常清除；
- 新文档布局：稳定文档位于 `docs/`，版本文档与报告位于 `docs/v0.24/`，历史根目录材料原样归档到 `docs/archive/pre-v0.24/`。

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

## 多 seed 长期分析

```bash
python -m subject_evolution.long_run_analysis \
  runs/mortality_trace_adaptive_groups_multiseed/seed_10001/evolution_progress.jsonl \
  runs/mortality_trace_adaptive_groups_multiseed/seed_10002/evolution_progress.jsonl \
  runs/mortality_trace_adaptive_groups_multiseed/seed_10003/evolution_progress.jsonl \
  --output analyses/mortality_trace_adaptive_groups
```

长期分析同时报告原始相关、首差分、控制 tick 与人口后的偏相关、cross-lag、局部区域面板、局部文化流和事件窗口。它们仍是观察性证据，不能替代 checkpoint 配对干预。

## v0.24 自然事件配对矩阵

先生成不可静默修改的锚点 manifest：

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

检查 `natural_event_matrix_manifest.json` 的锚点、计划哈希和干预可识别性后，可在同一命令中增加：

```bash
--execute --backend cpu
```

执行时，每个 intervention 与 baseline 从**同一个事件前 `.sechk`** 开始，使用相同 keyed randomness。事件是自然发生、并非随机分配，因此该矩阵识别的是“给定所选事件与短期窗口的机制消融效应”，不是环境暴露本身的随机试验效应。

## checkpoint 与单项重放

```bash
python -m subject_evolution.cli \
  --resume-checkpoint runs/example/checkpoint_00000600.sechk \
  --output runs/resumed \
  --backend cpu \
  --until-tick 720
```

```bash
python -m subject_evolution.replay \
  --checkpoint runs/example/checkpoint_00000600.sechk \
  --output runs/transfer_off \
  --until-tick 720 \
  --intervention disable-knowledge-transfer \
  --backend cpu
```

v0.24 新增的群组刷新消融名称为：

```text
freeze-group-refresh
```

`.sechk` 使用 pickle 载荷，只能加载本项目生成且来源可信的 checkpoint。

## 核心能力概览

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

## 稳定文档

- [当前项目状态](docs/PROJECT_STATUS.md)
- [科学问题与研究债务](docs/SCIENTIFIC_ISSUES.md)
- [变更记录](docs/CHANGELOG.md)
- [架构与提交边界](docs/ARCHITECTURE.md)
- [v0.24 文档与验证索引](docs/v0.24/README.md)

旧版根目录报告未删除，统一保存在 `docs/archive/pre-v0.24/`。归档内容只用于历史追溯，不代表当前实现状态。

## 当前主要未完成项

- 真实 CUDA `hybrid-accelerated` 世界循环的长程逐阶段 parity；
- 任意可配置的信息通道 schema；
- 通用、持久、任意嵌套主体图数据库；
- 完整设备驻留的关系、生命周期、主体图与日志提交；
- 多 GPU；
- Hero 强化学习；
- 经因果矩阵支持的主体性或主体偏移评分。
