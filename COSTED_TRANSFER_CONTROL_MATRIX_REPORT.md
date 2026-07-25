# 有代价传播 120-tick 验证报告（v0.18.0）

## 条件

- 配置：`mvp_short_latent_l2_memory_topk_inherited_heterogeneous_budget_matched_costed_transfer_longrun.json`
- seed：`10001`
- backend：CPU strict-reference
- 终点：120 ticks
- 双重复：是

## 结果

| 指标 | 数值 |
|---|---:|
| Alive | 1023 |
| Proposals | 546 |
| Attempts after attention | 545 |
| Commits | 447 |
| Commit rate | 82.02% |
| Bytes committed | 26,920 |
| Cross-lineage commits | 396 |
| Same-lineage commits | 51 |
| Cross-group commits | 2 |
| Unknown-group commits | 436 |
| Active transferred roots | 391 |
| Effective transferred roots | 365.4454 |

双重复核心日志逐字节一致；tick 60/120 checkpoint 与从 tick 60 恢复的连续状态均完全一致。

该结果证明有代价传播路径实际执行并可审计，但不证明传播提高适应性或形成主体。
