# Checkpoint-common boundary diagnostics

## 问题

`freeze-group-refresh` 改变后续使用的群组标签，而 `spatial_local_region_boundary_cohesion` 又按分支当前标签划分内部/跨边界分享。因此该干预与原 cohesion 指标存在测量耦合：数值变化可能来自社会流变化，也可能只来自边界定义变化。

## v0.26 诊断

每条 natural-event trajectory 从同一 checkpoint 加载后、应用干预前冻结：

- 活跃实体稳定 ID；
- 当时的群组 token；
- snapshot tick。

后续分享事件同时按两种边界记账：

1. 分支当前群组标签；
2. checkpoint-frozen common boundary。

稳定 ID 与物理槽必须同时匹配。槽位复用后的新生实体不会继承旧成员身份，而被视为共同边界之外。该诊断只读取已提交分享事件，不进入策略、关系、群组刷新、资源、知识或生命周期提交。

schema：

```text
checkpoint-frozen-stable-entity-boundary-v1
```

新增局部字段包括：

```text
spatial_local_region_reference_benefit_internal
spatial_local_region_reference_benefit_cross_boundary
spatial_local_region_reference_benefit_unbounded
spatial_local_region_reference_boundary_cohesion
spatial_local_region_boundary_definition_gap
```

natural-event results v3 同时报告当前标签累计 cohesion、共同边界累计 cohesion 与两者差值。共同边界累计 cohesion 是评价 `freeze-group-refresh` 的首选口径。

## 边界

共同边界解决的是评价分区不一致，不解决自然事件非随机、区域人口迁移构成或三 seed 样本量问题。checkpoint 必须与 local diagnostic window 对齐，否则 v0.26 拒绝启用该诊断。
