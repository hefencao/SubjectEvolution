# 输入 analyses 结果评估

## 完整性

`analyses.zip` 包含三组 execution plan、preflight 和 paired results：

| 结果集 | Anchors | Trajectories | 作用 |
|---|---:|---:|---|
| common boundary rerun | 6 crowding | 8 | 重新评价 freeze-group-refresh |
| remaining event replication | 12 mortality/scarcity | 48 | transfer、group refresh、affinity 跨事件复制 |
| remaining mechanism ablation | 6 crowding | 16 | policy、working memory、Top-k |

三组 preflight 均表明执行与完整审计可用，checkpoint/config/progress hash 无失败。四份结果共享 manifest SHA-256 `737312dd...91dbb`。

## 综合覆盖

与最初 crowding 结果合并后：

- 18 个 manifest anchors 全部出现；
- 72 个 eligible anchor–intervention pairs 已执行；
- manifest 总 eligible pairs 为 108；
- 缺少 36 pairs：mortality/scarcity × policy、working memory、Top-k；
- 所有现有结果均无 event cohort endpoint decomposition。

## 支持的结论

1. `disable-knowledge-transfer` 在三类事件中都一致降低 active transferred roots、incoming/outgoing commits 和 new roots。它是传播维持局部文化状态的机制近端复制。
2. `freeze-group-refresh` 的 current-label cohesion 在三类事件中下降，但 checkpoint-common cohesion 没有重复方向；大部分表观效应来自评价分区改变。
3. neutralize affinity 与 memory ablation 的 regional alive 方向不能解释为存活收益，因为区域人口包含迁移和出生构成。

## 不支持的结论

- 传播提高人口或适应度；
- 群组刷新提高共同社会凝聚；
- 资源亲和或工作记忆普遍有害；
- 文化根、群组 cohesion 或区域人口能单独证明主体性。
