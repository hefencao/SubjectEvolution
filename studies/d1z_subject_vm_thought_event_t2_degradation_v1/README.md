# ThoughtEvent T2：前向 recall 前退化审计

本分支实验只读观察 T1 已实现的统一 ThoughtEvent arena，不增加 read head、前向 recall、retention policy、语言、SignalEvent 世界频道、`RETHINK`、`NO_ACTION` 或 confidence gate。

使用两个既有 fixed-bootstrap readout 对照：

- `duplicate-coordinate-control`：ports 29/30 均读取 objective input port 11，作为 rank-one collapse 负对照；
- `rank-two-candidate`：port 29 读取 11，port 30 读取 7，作为当前 Stage 3C rank-two 候选。

两臂共享 seed、世界状态、action output、event identity 和 sampled probability，只允许 token coordinate 30 不同。审计 emission、exact/near duplicate、跨 tick 漂移、跨主体相似度、中心化秩、arena occupancy、expiry、overwrite、parent count 和计数成本。
