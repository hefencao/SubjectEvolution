# K1 实现说明

## 语义边界

K1 的知识不是控制器。策略调用仍只接收既有观察和 128 个遗传策略权重。知识系统
在成功的信号行动之后生成交换计划，在生存成本阶段扣除存储成本，并在死亡提交后
清理持有者副本。不存在知识到 logits、control proposal 或 intent 的调用路径。

## 数据结构

`KnowledgeCatalog` 是追加式不可变内容目录；`KnowledgeArena` 是动态 SoA 副本区。
两者使用容量倍增，不再逐条 `np.append`。arena 增量维护 holder→rows 索引，避免传输
热路径反复全量重建。

`KnowledgeObservationPlan` 每 tick 发布只读、holder 分段数组。该计划是 K2/K3 的
稳定边界；K1 仅验证其内容与生命周期，不让策略读取。

## 传输阶段

1. 输入仅来自已通过 action conflict resolver 的 `SIGNAL` 行；
2. 根据独立无状态随机流选择是否尝试传输和发送副本；
3. 按 receiver ID、sender ID 规范排序并执行注意力槽仲裁；
4. 使用现有信息配置的 `channel_loss` 与 `classification_error`；
5. 发送成本在传输丢失时仍支付；接收成本只在可提交副本时支付；
6. 损坏创建新内容并记录原内容为 `parent_content_id`；
7. 容量不足时只按最旧 copy ID 淘汰，不检查内容、后果或所谓“正确性”。

## 输出

- `knowledge_events.jsonl`：逐 tick 汇总；
- `knowledge_transfers.csv`：逐传输计划与最终状态（配置可关闭）；
- `metrics.csv`：副本、内容、变体、成本、传输、拒绝、遗忘和淘汰指标；
- checkpoint：目录与活跃副本全部 SoA 数组；
- `run_metadata.json`：最终知识汇总；
- `scientific_validity.json`：明确 `knowledge_policy_influence=false`。

## 验证结果

详见：

- `K1_VALIDATION_REPORT.json`：同 seed 两次有代价交换运行的一致性；
- `K1_CONTROL_MATRIX_REPORT.json`：四条件对照及零成本失效对照；
- `tests/test_knowledge.py`：损坏变体、成本、容量淘汰、注意力仲裁和零影响语义测试。
