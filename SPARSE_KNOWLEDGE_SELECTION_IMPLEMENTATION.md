# v0.13.0 稀疏知识选择实现说明

## 定位

`sparse-query-key-topk-router-v1` 在完整动态知识 SoA 与现有 L2 路由之间增加一个稀疏选择层。它只创建每 tick 可重建的临时工作集，绝不把固定槽位写回权威知识状态。

没有使用全局 Category Embedding、固定类别 Token 语义或 Softmax Attention。

## Query 与 Key

实体 Query 来自：

- 四维公开宿主状态；
- 四维量化工作记忆；
- 宿主遗传的量化 Query 权重与偏置。

知识 Key 来自内容自身的可变长度 latent 投影，并继续注入该副本的局部五维后果。可靠性只调节证据强度，不赋予任何潜坐标预设意义。

评分采用稳定整数点积，随后按可靠性缩放并裁剪。不存在 `exp`、除法归一化或全局词表。

## Stable Top-k

每个实体只在当前 context 匹配的实际副本中选择。排序键为：

```text
-score_q, copy_id, content_id
```

因此分数相同也有跨排列稳定的结果。`K=0` 明确选择空集；候选少于 K 时全部选择。

选中的 `(copy_id, content_id, score_q)` 写入审计计划，随后只有这些副本进入既有 L1/L2 latent router。未选知识仍可维护、验证、复制和形成谱系，只是不参与本 tick 的策略 residual。

## 临时工作集

GPU/CPU 路由可将选中副本打包成密集矩阵，但该矩阵具有 `ephemeral-workset-only` 语义：

- 不限制宿主真实知识数量；
- 不影响内容去重或副本独立状态；
- 不改变 K4 谱系；
- 下一 tick 从权威 SoA 重新构造。

## 成本

选择成本为：

```text
base + candidate_count × per_candidate + selected_count × per_selected_copy
```

即使 `K=0` 或选中副本最终产生零 residual，候选扫描和 Top-k 工作仍会计费。选择成本与 L2 路由成本一起进入现有 all-or-none per-entity 预算审核。

## 审计与 parity

新增 `knowledge_selection_events.csv` 和 metrics：候选数、选中数、ties、阈值、选中 IDs、选择能耗及所减少的 MAC。

首版正式选择由 CPU-reference 稳定整数排序负责；hybrid GPU 仍可计算选中工作集的整数 L2 路由。当前环境没有 CUDA，真实 hybrid 多 tick parity 尚未验证。
