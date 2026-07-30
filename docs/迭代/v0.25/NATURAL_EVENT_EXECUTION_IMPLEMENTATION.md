# Natural-event execution v1

## 目标

v0.24 固定了暴露盲选锚点，但原执行入口仍将规划与执行放在同一模块中，并逐锚点重复运行共享 checkpoint。v0.25 新增独立执行层：

```text
subject_evolution.natural_event_execution
```

该层不读取结果来重选锚点，不修改 manifest，也不改变世界规则。

## 执行计划

输入已通过计划哈希校验的 manifest，输出：

```text
natural-event-execution-plan-v1
```

计划记录：

- manifest SHA-256；
- 路径映射；
- seed/event/anchor/intervention 过滤条件；
- 选中的完整锚点；
- source progress/config 审计项；
- 去重后的 trajectory；
- naive branch 数、trajectory 数和节省比例；
- execution-plan SHA-256。

## 路径移植

manifest 保留原始绝对路径。`--path-prefix OLD=NEW` 仅在执行计划中解析路径，不回写 manifest。多个映射按最长 OLD 前缀优先。

## 哈希预检

`natural-event-execution-preflight-v1` 分别报告：

- `execution_ready`：全部所需 checkpoint 存在且 SHA-256 一致；
- `full_audit_ready`：checkpoint、progress、resolved config 全部存在且 SHA-256 一致。

默认执行要求 full audit。`--checkpoint-only-preflight` 是显式降级，不改变 manifest 的计划哈希。

## 共享轨迹

只有 checkpoint hash 和 intervention 完全相同的分支才合并。合并轨迹运行到该组 anchor 所需的最大 tick。不同 region、event tick 和 horizon 的 summary 仍独立计算。

## 断点续跑

每条完成轨迹写：

```text
natural_event_trajectory.json
```

复用条件：

- manifest SHA 相同；
- checkpoint SHA 相同；
- intervention 相同；
- 已完成 tick 不小于计划 tick；
- `evolution_progress.jsonl` 存在。

不完整目录默认报错，防止将部分结果误当作完成结果。

## 聚合

结果 schema 升级为：

```text
natural-event-paired-intervention-results-v2
```

同时输出 anchor-level 与 seed-level 描述统计。seed-level 先在同一 seed、event kind、intervention、metric 内平均多个 anchors，再跨 seed 统计均值和正/负/零方向。

三 seed 仍不足以支持显著性推断，输出不计算 p-value。
