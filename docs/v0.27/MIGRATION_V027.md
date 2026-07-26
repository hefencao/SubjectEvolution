# Migration to v0.27

## 配置与默认世界

无需修改现有 simulation JSON。v0.27 新功能属于 natural-event execution 诊断层，普通 CLI、多 seed 长跑和 checkpoint 世界语义不变。

## Execution plan

- v1/v2 plan 可读取；
- 从 manifest 新建计划时默认生成 v3，并启用 event cohort；
- 历史兼容可使用 `--no-event-cohort-audit`，但会失去人口构成解释；
- signed `--execution-plan` 不允许追加 diagnostic/filter/path 参数。

## 结果

- v2/v3 paired results 可由 audit/synthesis 读取；
- 新执行输出 v4；
- 旧结果没有 cohort 字段时不会伪装成已分解；
- 多批旧/新结果可由 result synthesis 合并，前提是 manifest hash 和核心世界结果一致。

## Marker 与续跑

启用 cohort 的 v3 plan 要求 v3 trajectory marker。旧 marker 即使世界轨迹存在，也不会被静默复用，因为它没有 anchor-specific event stable-ID snapshot。
