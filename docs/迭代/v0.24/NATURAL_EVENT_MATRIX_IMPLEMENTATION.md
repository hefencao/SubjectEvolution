# Natural-event paired intervention matrix

## 目标

将已有单 run `local_event_counterfactual` 提升为跨 seed、可审核、可冻结的实验计划层，而不改变世界规则。

## 选择协议

Schema：

```text
exposure-only-local-peak-selection-v1
```

输入仅包括：

- tick；
- 区域 alive（只用于排除数值空区域）；
- 区域 resource scarcity；
- 区域 crowding；
- 区域 mortality pressure；
- `.sechk` checkpoint 可用性。

选择阶段不读取：cohesion、incoming/outgoing transfer、new/lost/active roots、谱系集中、动作熵或任何事后 branch outcome。

每个 region 使用自身有效窗口计算 quantile、均值和标准差；只选择超过阈值的局部峰值，并通过 `min_gap_windows` 和优先不同 region 的规则减少重复锚点。

## Manifest

Schema：

```text
natural-event-paired-intervention-matrix-v1
```

每个 anchor 包含：

- run、seed、event kind、region、event tick；
- exposure value、region threshold、z-score；
- 严格早于 event tick 的最近完整 checkpoint；
- progress/config/checkpoint SHA-256；
- branch until tick；
- 每个 intervention 的 eligible/reason。

完整 manifest 使用 canonical JSON 计算 `plan_sha256`。加载或执行前重新计算；任何改动都会失败。

可选的 long-run analysis JSON 只记录 schema、hash 和 repeated patterns，字段 `used_for_anchor_selection=false`。

## 默认矩阵

```text
disable-knowledge-transfer
disable-knowledge-policy
ablate-working-memory
bypass-sparse-selection
freeze-group-refresh
neutralize-resource-affinity
neutralize-danger-evidence
```

planner 根据 resolved config 和 checkpoint 前累计状态判断可识别性。当前旗舰三 seed 的 danger evidence 为 disabled，因此该项会保留在审计表中但不执行。

## freeze-group-refresh

- 不修改现有 group IDs 或方向；
- 不清空关系；
- 不新增控制器；
- 后续 periodic/adaptive group refresh 全部跳过；
- 死亡成员的 group state 仍清零；
- 新生实体保持未分组；
- 状态进入 checkpoint、clone、metrics 和 intervention history。

该干预估计“事件后继续刷新群组标签”的短期作用，不等价于从世界开始就没有群组，也不等价于删除社会关系。

## 命令

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

审核 manifest 后增加 `--execute --backend cpu`。执行结果写入 `natural_event_matrix_results.json/md`。

## 当前输入限制

本次用户附加的是聚合 analysis，而不是包含 `.sechk` 的三个原始 run 目录，因此包内没有伪造实际锚点 manifest。应在原运行机器上对 `runs/mortality_trace_adaptive_groups_multiseed` 执行上述命令。
