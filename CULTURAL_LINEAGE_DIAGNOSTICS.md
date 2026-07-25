# 文化知识谱系诊断（v0.18.0）

## 三类知识根必须分开

1. **全部知识根**：包括私有经验、transfer 副本和损坏变体；
2. **transfer-derived roots**：当前至少有一个活跃 `ACQUISITION_TRANSFER` 副本的根；
3. **历史成功传播事件**：累计成功 host transition，不要求副本当前仍存活。

v0.17 主要统计第 1 类，因此不能把高 root-lineage enrichment 自动解释为文化传播。

## 新指标

### 事件累计

```text
knowledge_transfer_proposals_total
knowledge_transfer_attempts_total
knowledge_transfer_committed_total
knowledge_transfer_committed_bytes_total
knowledge_transfer_cross_lineage_committed_total
knowledge_transfer_cross_group_committed_total
```

### 当前活跃文化状态

```text
knowledge_active_transferred_copy_count
knowledge_active_transferred_root_count
knowledge_effective_transferred_roots
knowledge_largest_transferred_root_holder_fraction
knowledge_transferred_root_multi_genetic_lineage_fraction
knowledge_transferred_root_multi_group_fraction
knowledge_transferred_root_genetic_lineage_pair_enrichment
knowledge_transferred_root_group_pair_enrichment
```

事件累计回答“历史上发生了多少传播”，当前状态回答“传播产生的副本和根现在还剩多少”。两者不能互换。

## 变体规则

损坏传播产生的内容保留 `parent_content_id`，root 追溯到原始内容；因此一个传播根的多个损坏后代不会被错误计为完全独立文化起源。

## 解释要求

- `committed_total == 0`：文化传播不可解释；
- `committed_total > 0` 但 active transferred roots 为 0：历史发生过传播，但当前文化副本已经灭绝；
- transferred root 跨多个遗传世系：支持跨遗传背景传播，但不等于适应优势；
- transferred root 跨多个 group：支持跨社会边界传播，但不等于群组因果机制。
