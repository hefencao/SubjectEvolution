# v0.28 输入 analyses 评估

## 输入完整性

用户提供的 `analyses.zip` 包含三份 v0.27 signed execution plan 的输出目录：

| 批次 | Anchors | Plan trajectories | Preflight | Results |
|---|---:|---:|---|---|
| `primary_event_cohort_rerun` | 18 | 64 | execution/full-audit 均通过 | 完成 |
| `crowding_knowledge_cohort_rerun` | 6 | 16 | execution/full-audit 均通过 | 完成 |
| `remaining_event_knowledge_cohort_rerun` | 12 | 48 | execution/full-audit 均通过 | **未附结果文件** |

因此本轮可综合的覆盖仍是 18 anchors、72/108 eligible anchor–intervention pairs。缺少的 36 pairs 仍是 mortality/scarcity 下的 `disable-knowledge-policy`、`ablate-working-memory`、`bypass-sparse-selection`。

## 新发现的执行时序问题

v0.27 cohort 恒等式本身成立，但这些分支在 prior checkpoint tick 就应用干预，而名义 event tick 晚 30 或 60 ticks：

- 72/72 个已执行 pairs 的 intervention history 都早于 event tick；
- 42 pairs 提前 30 ticks，30 pairs 提前 60 ticks；
- 48/72 pairs 在 event tick 的区域 alive 数已经与 baseline 不同；
- 旧 cohort schema 没有稳定 ID 集合哈希，因此其余 24 个“人数相同”也不能证明实体身份相同。

这意味着 v0.27 结果估计的是“在事件前 checkpoint 开始改变机制后，直到 horizon 的总效应”。它可以改变名义事件暴露、事件时区域人口和 cohort 构成，不能直接解释为“事件发生后机制的短期效应”。

## 对现有结果的保留方式

旧结果不作废，但必须重新命名解释：

- `checkpoint-immediate-v1`：干预从 prior checkpoint 开始；
- 适合研究机制对事件形成前后整段轨迹的影响；
- 不适合把 branch-specific event cohort delta 当作共同事件 cohort 的因果分解；
- transfer/root、group boundary 和区域人口方向继续保留为描述性结果，不升级为 event-conditional 结论。

## v0.28 决策

v0.28 新增独立的 event-timed execution：

1. 从签名 source checkpoint 只演进一次共同前史到 event tick；
2. 保存带 state/file SHA-256 的 event checkpoint；
3. baseline 与全部 interventions 从该同一 checkpoint 分支；
4. 在应用干预前冻结 common boundary 和 event cohort；
5. cohort 发布全局与区域 stable-ID SHA-256，逐 pair 验证完全相同。

该改动只改变实验执行边界，不改变世界动力学或基础模型参数。
