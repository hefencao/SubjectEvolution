# Event-timed natural-event execution

## 目标估计量

`subject_evolution.natural_event_timed_execution` 估计：

> 在一个预注册、自然发生的名义事件状态已经形成后，于 event tick 改变某一机制，对后续固定 horizon 世界轨迹的短期影响。

它不估计事件暴露本身的因果作用，也不把自然事件随机化。

## 两阶段执行

### Shared prefix

每个 `(source checkpoint SHA-256, event tick)` 组合只重放一次：

```text
signed source checkpoint
        │
        └── deterministic replay ──> event checkpoint
```

prefix marker 绑定：

- execution-plan SHA-256；
- source checkpoint SHA-256；
- source/event tick；
- event checkpoint file SHA-256；
- event checkpoint semantic state SHA-256；
- backend 与 GPU semantics mode。

### Post-event branches

```text
event checkpoint
  ├── baseline
  ├── intervention A
  ├── intervention B
  └── intervention C
```

每条 branch 在干预前执行：

1. checkpoint-common boundary freeze；
2. event cohort capture；
3. stable-ID global/region cohort hash publication；
4. intervention application（baseline 跳过）；
5. 运行到该 anchor 的 signed horizon。

## Pairing proof

每个 eligible pair 输出 `shared-event-checkpoint-pairing-v1`：

- `event_alive_equal`；
- `event_global_identity_equal`；
- `event_region_identity_equal`；
- `valid`。

只有三个条件全部成立，人口 cohort delta 才能解释为同一 event cohort 的分支差异。

## Schema

- plan: `natural-event-timed-execution-plan-v1`
- prefix marker: `natural-event-shared-prefix-v1`
- trajectory marker: `natural-event-timed-trajectory-v1`
- result: `natural-event-timed-paired-intervention-results-v1`
- pairing: `shared-event-checkpoint-pairing-v1`
- cohort: `event-region-endpoint-cohort-decomposition-v2`

旧 checkpoint-immediate executor 继续存在，并在 v0.28 明确输出 `intervention_timing="checkpoint-immediate-v1"`。两种估计量不得在同一 synthesis 中合并。

## 命令

从 manifest 生成计划：

```bash
python -m subject_evolution.natural_event_timed_execution \
  --manifest analyses/natural_event_matrix/natural_event_matrix_manifest.json \
  --event-kinds crowding,mortality,scarcity \
  --interventions disable-knowledge-transfer,freeze-group-refresh,neutralize-resource-affinity \
  --output analyses/event_timed_primary
```

完整哈希预检后执行：

```bash
python -m subject_evolution.natural_event_timed_execution \
  --execution-plan analyses/event_timed_primary/natural_event_timed_execution_plan.json \
  --output analyses/event_timed_primary \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

signed plan 模式不接受额外筛选或路径修改。

## 算力边界

当前 manifest 的三份计划为：

| 计划 | Prefixes | Post-event trajectories |
|---|---:|---:|
| primary 三机制 × 全部事件 | 18 | 72 |
| crowding knowledge 三机制 | 6 | 24 |
| mortality/scarcity knowledge 三机制 | 12 | 48 |

相比从 prior checkpoint 为每个 branch 重跑，prefix 只演进一次；代价是不同 event tick 不再错误共享同一已干预 trajectory。
