# v0.21 自适应群组标签刷新

## 为什么不能直接关闭群组标签

`group_id` 并非纯报告字段。它参与：

- partner group-match observation；
- social signal；
- group direction；
- 知识上下文；
- 知识传播的同组/跨组审计；
- 利益边界分类。

因此全局禁用更新会改变主体控制语义，并使长期群组年龄和传播分类失真。

## 新 schema

```text
adaptive-topology-v1
```

旧配置仍使用：

```text
periodic-v1
```

兼容默认没有改变。

## 调度条件

自适应模式在初始 tick 建立标签，此后只有满足最小间隔并出现以下条件之一才重算：

1. 有效关系拓扑跨越群组 trust threshold；
2. 实体死亡、关系目标死亡或生命周期重置令现有标签可能陈旧；
3. 延迟衰减预计使某条当前有效关系跌破 threshold；
4. 达到最大陈旧期限。

正式长跑配置：

```text
group_update_min_period = 100
group_update_max_period = 300
```

所有触发都受 minimum period 限速，避免关系变化频繁时反而比周期模式重算更多。

## 审计

新增持久状态和指标：

- `group_labels_dirty`
- `last_group_dirty_reason`
- `last_group_update_tick`
- `last_group_update_reason`
- `next_group_decay_due_tick`
- `group_update_count`
- `group_update_skipped_count`

更新原因与 dirty 原因分开保存，避免后续出生/死亡覆盖上一次真实更新原因。

## 语义边界

自适应刷新不是 periodic 模式的无损性能替换。减少重算会延长标签持有时间，因此可能改变策略轨迹。它作为显式实验 schema 启用，旧配置继续保持逐周期重算。
