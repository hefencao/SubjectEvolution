# 有代价知识传播审计（v0.18.0）

## 问题来源

用户提供的三 seed `multi-seed-long-run-analysis-v2` 同时出现：

- `knowledge_transfer_probability = 0.1`；
- `knowledge_transfer_committed_final = 0`；
- `knowledge_cultural_spread_interpretable = true`。

这不是“配置启用但世界没有传播”的可靠证据，而是两个诊断问题叠加：

1. v0.17 的 `evolution_progress.jsonl` 没有写入累计传播字段，离线分析器读取缺失字段时默认成 0；
2. v0.17 只要配置概率大于 0 就把文化传播标记为可解释，即使没有任何成功提交。

此外，旧 `knowledge_root_genetic_lineage_pair_enrichment` 使用全部知识根，其中包含每个宿主独立创建的私有经验，不能单独解释为文化传播。

## 实际运行语义

传播触发 schema 为：

```text
signal-action-partner-v1
```

只有实体选择 `SIGNAL`、形成有效接收者，并通过 `transfer_probability` 门控后，才会形成传播提案。传播概率不是每实体每 tick 的独立广播概率。

传播流水线记录：

```text
proposal
→ attention admission
→ sender energy
→ channel delivery/corruption
→ receiver energy
→ duplicate/capacity arbitration
→ committed copy
```

## v0.18 修复

每个长期窗口现在同时写出：

- proposals、admitted attempts、delivered、lost、corrupted；
- committed 数量与真实字节；
- duplicate、capacity、energy、attention 拒绝；
- same/cross/unknown founder lineage commits；
- same/cross/unknown group commits；
- sender/receiver 能耗；
- 仅由 `ACQUISITION_TRANSFER` 副本构成的 transferred-root 指标。

`knowledge_cultural_spread_interpretable` 只有在累计成功提交大于 0 时才为真。

## 120-tick 验证

配置：

```text
mvp_short_latent_l2_memory_topk_inherited_
heterogeneous_budget_matched_costed_transfer_longrun.json
seed = 10001
CPU strict reference
```

最终：

| 指标 | 数值 |
|---|---:|
| 传播提案 | 546 |
| attention 后尝试 | 545 |
| 成功提交 | 447 |
| 提交率（attention 后） | 82.02% |
| 提交字节 | 26,920 |
| 跨 founder lineage 提交 | 396 |
| 同 founder lineage 提交 | 51 |
| 跨 group 提交 | 2 |
| 同 group 提交 | 9 |
| group 未形成/未知时提交 | 436 |
| 活跃 transferred roots | 391 |
| 有效 transferred roots | 365.4454 |
| 最大 transferred root 持有份额 | 0.7126% |

早期多数传播发生在群组形成前，所以 group 分类为 unknown 并不表示记录丢失。

## 科学边界

成功传播证明配置的文化复制路径确实运行，但不能直接证明：

- 传播提高适应性；
- 某个知识根具有主体性；
- 跨世系传播导致凝聚度变化；
- 传播独立维持长期文化多样性。

这些问题需要 phase checkpoint 下的 `disable-knowledge-transfer` 配对分支和多 seed 长周期 transferred-root 诊断。
