# Subject Evolution v0.14.0 交付物索引

## 1. 顶层交付

| 文件 | 说明 |
|---|---|
| `subject_evolution_v014_project.zip` | v0.14.0 源码、配置、测试和报告 |
| `subject_evolution_v014_project.tar.gz` | 同一源码的 TAR.GZ |
| `subject_evolution_v014_results.zip` | v0.14 短实验、消融结果和日志 |
| `subject_evolution_v014_results.tar.gz` | 同一结果的 TAR.GZ |
| `subject_evolution_v014.patch` | v0.13 -> v0.14 差异补丁 |
| `subject_evolution_v014_SHA256SUMS.txt` | 原交付哈希 |

## 2. 当前状态和入口

| 文件 | 用途 |
|---|---|
| `PROJECT_STATUS.md` | 当前已完成/未完成与下一步 |
| `SPLIT_MANIFEST.md` | 模块拆分和各版本新增文件 |
| `FINAL_TEST_REPORT.txt` | 最终单元测试明细 |
| `pyproject.toml` | 包版本、Python 和依赖 |

## 3. 当前阶段报告

| 文件 | 用途 |
|---|---|
| `EVOLVABLE_SELECTION_IMPLEMENTATION.md` | v0.14 遗传 Top-k 容量设计 |
| `EVOLVABLE_SELECTION_CONTROL_MATRIX_REPORT.md` | 固定 K/遗传 K 短对照与消融摘要 |
| `EVOLVABLE_SELECTION_VALIDATION_REPORT.json` | 机器可读 v0.14 验证 |
| `CAUSAL_ABLATION_IMPLEMENTATION.md` | 记忆消融和选择器旁路语义 |
| `V013_V014_COMPATIBILITY_REPORT.json` | 固定 K 兼容性 |

## 4. 历史阶段实现说明

- `K1_IMPLEMENTATION.md`
- `K2_IMPLEMENTATION.md`
- `K3_IMPLEMENTATION.md`
- `K4_IMPLEMENTATION.md`
- `CHECKPOINT_REPLAY_IMPLEMENTATION.md`
- `LATENT_KNOWLEDGE_IMPLEMENTATION.md`
- `LATENT_ROUTER_MLP_IMPLEMENTATION.md`
- `LATENT_ROUTING_COST_IMPLEMENTATION.md`
- `WORKING_MEMORY_IMPLEMENTATION.md`
- `SPARSE_KNOWLEDGE_SELECTION_IMPLEMENTATION.md`
- `CPU_GPU_PARITY.md`
- `PERIODIC_POSITION_FIX.md`

## 5. 关键源码

| 文件 | 说明 |
|---|---|
| `simulation.py` | 世界主循环和阶段提交 |
| `knowledge.py` | K1/K2 知识权威状态和事件 |
| `knowledge_policy.py` | K3 和潜路由的稀疏策略计划 |
| `knowledge_subjects.py` | K4 候选主体诊断 |
| `latent_knowledge.py` | 变长潜内容、L1/L2、Top-k 和容量解析 |
| `working_memory.py` | 定点工作记忆 |
| `routing_cost.py` | 计算成本和预算仲裁 |
| `checkpointing.py` | `.sechk` |
| `replay.py` | 离线恢复/分支 CLI |
| `interventions.py` | 科学干预 |
| `parity.py` | CPU/GPU 首差异定位 |
| `gpu_runtime.py` | hybrid 设备路径 |

## 6. 关键配置

- `configs/mvp_short_latent_l2_memory_topk_inherited.json`：v0.14 当前最高能力短配置；
- `configs/mvp_short_latent_l2_memory_topk4.json`：固定 K=4 兼容基线；
- `configs/mvp_short_latent_l2_budget_matched.json`：L2 预算匹配；
- `configs/mvp_short_replay.json`：完整 checkpoint；
- `configs/mvp_short_k4_candidates.json`：K4；
- `configs/mvp_short_k2_exchange.json`：K2 交换和历史真实 GPU parity；
- `configs/mvp_small_k2.json`：较大 K2 场景。

## 7. 结果目录样例

`subject_evolution_v014_results/runs/inherited_a/` 和 `inherited_b/` 是 v0.14 双重复。`ablate_memory/` 与 `bypass_selection/` 为 checkpoint 分支结果。

## 8. 本交接包

- `00_README_FIRST_CN.md`
- `01_PROJECT_OVERVIEW_CN.md`
- `02_PROJECT_PROGRESS_CN.md`
- `03_ARCHITECTURE_AND_SCIENCE_BOUNDARIES_CN.md`
- `04_RUNBOOK_CN.md`
- `05_HANDOFF_REPORT_CN.md`
- `06_NEW_CHAT_BOOTSTRAP_PROMPT_CN.md`
- `07_ARTIFACT_INDEX_CN.md`
- `08_VERSION_AND_SCHEMA_MATRIX_CN.md`
- `PROJECT_HANDOFF_PACKAGE_CN.docx`
- `PROJECT_HANDOFF_PACKAGE_CN.pdf`
