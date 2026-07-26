# 用户 natural-event manifest 评估

## 输入

- schema：`natural-event-paired-intervention-matrix-v1`
- selection：`exposure-only-local-peak-selection-v1`
- plan SHA-256：`737312dd4659807a89323fd275e784b91166fbaa53cdf094b16ca24618091dbb`
- horizon：120 ticks

## 结构检查

manifest 含 18 个锚点，严格平衡为：

```text
3 seeds × 3 event kinds × 2 anchors = 18 anchors
```

每个锚点只使用 tick、区域 alive、对应 exposure 和 checkpoint 可用性。事后凝聚度、传播流、文化根、有效谱系、最大谱系和动作熵均被排除，analysis JSON 仅用于 rationale/audit。

每个锚点有六个 eligible interventions：

- `disable-knowledge-transfer`
- `disable-knowledge-policy`
- `ablate-working-memory`
- `bypass-sparse-selection`
- `freeze-group-refresh`
- `neutralize-resource-affinity`

`neutralize-danger-evidence` 在全部锚点均正确标记为 ineligible，因为该长跑配置的 danger evidence schema 为 disabled。

## 执行规模

直接逐锚点执行需要：

```text
18 × (1 baseline + 6 eligible interventions) = 126 branches
```

manifest 实际只使用 16 个唯一 checkpoint hash。seed 10001 的两个 crowding 锚点共享 tick-240 checkpoint；seed 10003 的两个 crowding 锚点也共享 tick-240 checkpoint。

v0.25 按 `(checkpoint SHA-256, intervention)` 合并轨迹，并运行到同组锚点需要的最大 `until_tick`：

```text
126 naive branches → 112 trajectories
减少 14 条轨迹，节省 11.1%
```

共享轨迹不合并 region summary；每个锚点仍按自己的 region、event tick 和 horizon 独立计算结果。

## 事件尺度注意事项

crowding 和 mortality 锚点的标准化分数约为 3.3–3.9，而 scarcity 约为 0.55–0.60。scarcity 原始值集中在约 0.997，说明该 exposure 在当前配置中接近饱和、跨窗口方差很小。

因此：

1. scarcity 锚点仍是各自区域内的高分位局部峰值；
2. 不应使用 z-score 跨 event kind 排序“事件强度”；
3. 结果必须按 scarcity、crowding、mortality 分层；
4. seed-level 汇总应先在每个 seed 内平均多个锚点，避免伪重复。

## 执行边界

本环境没有 manifest 中 `/home/unkloser/projects/SubjectEvolution/...` 的原始 run 和 checkpoint，因此只生成了执行计划，未伪造分支结果。用户机器可直接使用 `--path-prefix` 映射路径并重新预检。
