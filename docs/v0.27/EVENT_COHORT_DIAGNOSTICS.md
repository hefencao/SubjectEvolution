# Event cohort endpoint diagnostics

Schema：`event-region-endpoint-cohort-decomposition-v1`

## 目的

paired natural-event 结果原先只报告 `final_alive_region`。该值同时受事件时居民留存、迁出、死亡、既有实体迁入和事件后出生影响，不能直接解释为 survival。

## 身份快照

每个 anchor 在自己的 event tick 记录：

- `global_alive_ids_at_event`；
- `region_alive_ids_at_event`。

身份使用 stable entity ID。slot index 只用于当前读取，死亡后复用槽位的新实体不会继承 cohort 身份。

## 终点分解

- `final_event_cohort_retained_region`：事件时区域 cohort，终点仍在区域；
- `final_event_cohort_survived_outside_region`：cohort 终点存活但在区域外；
- `final_event_cohort_absent`：cohort 终点不再 alive；
- `final_existing_in_migrants_region`：事件时已存在但不在区域，终点迁入；
- `final_post_event_born_region`：事件后出生且终点在区域。

验证：

```text
final regional alive
= retained cohort + existing in-migrants + post-event-born

Δ regional alive
= existing in-migrants + post-event-born
- survived outside - absent
```

所有计数从同一终点状态重建，balance residual 非零即视为执行/分析错误。

## 边界

- 诊断不反馈世界；
- 不进入 checkpoint，因此只用于当前 execution trajectory；
- 共享世界轨迹可同时观察多个 anchor；
- 只分解终点，不能识别 horizon 内多次迁入迁出、死亡时点或中间出生后死亡；
- cohort 组件仍是自然事件条件下的 paired branch outcome，不随机化 exposure。
