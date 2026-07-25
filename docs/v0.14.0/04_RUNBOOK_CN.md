# Subject Evolution v0.14.0 运行与验证手册

## 1. 解压与环境

```bash
unzip subject_evolution_v014_project.zip
cd subject_evolution_v014_project
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
python -m pip install -U pip
python -m pip install -e .
```

项目声明的必需依赖只有 `numpy>=1.24`。GPU 运行还需要与本机 CUDA runtime 匹配的 CuPy，并确保 Python 能检测到可用设备。

若不执行 editable install，也可：

```bash
export PYTHONPATH="$PWD/src"
```

PowerShell：

```powershell
$env:PYTHONPATH = "$PWD\src"
```

## 2. 快速 CPU 冒烟

```bash
PYTHONPATH=src python -m subject_evolution.cli \
  --config configs/smoke_cpu.json \
  --output runs/smoke_cpu \
  --backend cpu
```

最新机制的 30-tick 短运行：

```bash
PYTHONPATH=src python -m subject_evolution.cli \
  --config configs/mvp_short_latent_l2_memory_topk_inherited.json \
  --output runs/v014_inherited \
  --backend cpu
```

## 3. GPU 模式

### 3.1 正式正确性优先

```bash
PYTHONPATH=src python -m subject_evolution.cli \
  --config configs/mvp_short_latent_l2_memory_topk_inherited.json \
  --output runs/v014_gpu_strict \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

该模式要求存在可用 GPU，但以 CPU reference 世界语义为权威，不代表获得 hybrid 加速。

### 3.2 实验 hybrid 路径

```bash
PYTHONPATH=src python -m subject_evolution.cli \
  --config configs/mvp_short_latent_l2_memory_topk_inherited.json \
  --output runs/v014_gpu_hybrid \
  --backend gpu \
  --gpu-semantics-mode hybrid-accelerated
```

v0.14 的真实 CUDA world parity 尚未完成；此输出不应自动作为正式科学基线。

## 4. 测试

```bash
PYTHONPATH=src python -m compileall -q src tests
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py' -v
```

当前权威结果：64 tests，63 passed，1 skipped（无 CuPy/CUDA）。

开发偏好：先跑相关单测和 20-50 ticks 短验证；只有问题在长轨迹出现时才扩展到更长运行。

## 5. CPU/GPU parity

短阶段检查：

```bash
PYTHONPATH=src python -m subject_evolution.parity \
  --config configs/mvp_short_latent_l2_memory_topk_inherited.json \
  --output runs/parity_v014 \
  --ticks 5 \
  --entities 64 \
  --device-backend auto
```

真实 hybrid world trace：

```bash
PYTHONPATH=src python -m subject_evolution.parity \
  --config configs/mvp_short_latent_l2_memory_topk_inherited.json \
  --output runs/parity_v014_world \
  --ticks 30 \
  --preserve-config-world \
  --world-only \
  --device-backend gpu \
  --require-gpu
```

优先关注首差异：

- requested Top-k capacity；
- selected copy/content IDs 与 score；
- working-memory state；
- L1/L2/knowledge logits；
- routing/selection cost；
- final action、intent、birth/death；
- 持久实体、环境、信息和知识状态。

## 6. 完整 checkpoint 与恢复

配置中启用：

```json
"full_checkpoint_enabled": true
```

运行后会生成 `checkpoint_XXXXXXXX.sechk`。

继续运行：

```bash
PYTHONPATH=src python -m subject_evolution.cli \
  --resume-checkpoint runs/v014_inherited/checkpoint_00000015.sechk \
  --output runs/v014_resumed \
  --until-tick 30 \
  --backend cpu
```

注意：`.sechk` 内含 pickle，只能加载项目自己生成且来源可信的文件。

## 7. 离线配对反事实

工作记忆消融：

```bash
PYTHONPATH=src python -m subject_evolution.replay \
  --checkpoint runs/v014_inherited/checkpoint_00000015.sechk \
  --output runs/ablate_memory \
  --until-tick 30 \
  --intervention ablate-working-memory \
  --backend cpu
```

选择器旁路：

```bash
PYTHONPATH=src python -m subject_evolution.replay \
  --checkpoint runs/v014_inherited/checkpoint_00000015.sechk \
  --output runs/bypass_selection \
  --until-tick 30 \
  --intervention bypass-sparse-selection \
  --backend cpu
```

其他科学干预可通过 `python -m subject_evolution.replay --help` 查看。

## 8. 常用配置

| 配置 | 用途 |
|---|---|
| `smoke_cpu.json` | 最短 CPU 冒烟 |
| `mvp_short_k2_exchange.json` | K2 交换与历史 GPU parity 基线 |
| `mvp_short_k4_candidates.json` | K4 候选图 |
| `mvp_short_replay.json` | 完整 checkpoint/replay |
| `mvp_short_latent_l1_costed.json` | L1 成本路径 |
| `mvp_short_latent_l2_budget_matched.json` | L2 预算匹配 |
| `mvp_short_latent_l2_memory.json` | 工作记忆 |
| `mvp_short_latent_l2_memory_topk4.json` | 固定 Top-k=4 |
| `mvp_short_latent_l2_memory_topk_inherited.json` | v0.14 实体级遗传 Top-k |
| `mvp_small_k2.json` | 较大 500-tick K2 场景，不作为日常测试默认项 |

## 9. 主要输出

- `metrics.csv`：周期指标；
- `summary.json`、`run_metadata.json`：最终摘要；
- `run_manifest.json`：版本、后端和 provenance；
- `scientific_validity.json`：科学有效性标记；
- `resolved_config.json`：实际配置；
- `knowledge_events.jsonl`；
- `knowledge_transfers.csv`；
- `knowledge_outcome_updates.csv`；
- `knowledge_policy_contributions.csv`；
- `knowledge_routing_costs.csv`；
- `knowledge_working_memory.csv`；
- `knowledge_selection_events.csv`；
- `checkpoint_*.npz`：分析快照；
- `checkpoint_*.sechk`：可信完整恢复包。

## 10. 常见故障

### `BackendUnavailableError`

CuPy/CUDA 不可用或不匹配。不要静默回退；先确认设备、驱动和 CuPy 安装。

### CPU/GPU alive 差 1

不要只比较最终 alive。运行 `subject_evolution.parity`，定位首个 tick、阶段、字段和稳定实体 ID。

### `periodic position invariant failed`

v0.6.5 已修复 float32 上界舍入。若再次出现，应检查是否有新代码直接写 `x/y` 而未使用 canonical half-open wrap；错误信息应包含 slot、entity_id 和坐标。

### parity 工具属性错误

不要猜对象字段。曾出现不存在的 `relation_target` 假设；修改 parity 时必须按实际类和 snapshot 结构检查。

### GUI 与 CLI 行为不一致

确认 GUI 使用同一个 `src` 和相同配置。当前 v0.14 项目包不含 GUI wrapper，用户本地 GUI 可能是外部目录。
