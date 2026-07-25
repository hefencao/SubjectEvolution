# 局部文化传播诊断（v0.20.0）

## 目标

v0.19 已证明全局人口稳定会掩盖区域压力，但只记录了全局传播提交数。v0.20 将成功知识传播投影到与局部压力相同的分析网格，以回答：文化知识从哪里产生、流向哪里、在哪些区域建立或消失，以及它是否与局部稀缺、拥挤和凝聚结构共同变化。

## 权威边界

新增诊断是纯观察模块，不参与策略、知识路由、关系、移动、资源、危险、繁殖或能量结算。完整知识仍保存在动态副本 arena 中，区域矩阵与文化根面板只是每个报告窗口可重建的审计状态。

启用 schema：

```text
spatial-local-stress-culture-diagnostics-v2
```

旧 `spatial-local-stress-diagnostics-v1` 语义保持不变。

## 传播空间审计

每次成功传播提交后记录：

- 发送者和接收者区域；
- 尝试数、成功提交数和提交字节；
- 同区域与跨区域传播；
- 每个区域的发送/接收 attempts、commits、bytes；
- 区域到区域的 attempt/commit/byte 矩阵。

区域归属根据提交时实体的周期世界位置确定，不创建环境边界，也不阻止跨区移动。

## 区域文化根状态

每个报告窗口对活跃 transfer-derived 副本按 `(holder, root_content)` 去重，记录：

- 每个区域活跃 transferred roots；
- 每个区域有效 transferred roots；
- 相对上一窗口新建立和消失的根；
- 同一根同时存在于多个区域的数量；
- 全局 active transferred-root presence 数。

私有经验根不会被计入文化根。损坏传播产生的变体仍归属于其 root content。

## 长期分析指标

v5 分析器分别给出 raw、region fixed-effect、window fixed-effect、first difference 和 next-window 关系，包括：

- 稀缺与 outgoing/incoming transfer rate；
- 稀缺与新文化根、净文化根建立；
- 凝聚度与同区域传播留存；
- 拥挤与 outgoing transfer rate；
- 死亡压力与 incoming transfer rate。

这些统计是事件选择依据，不是因果结论。

## 120-tick 管线验证

seed 10001、200 初始实体、16 区域：

- 111 proposals / 111 attempts / 89 commits；
- 5,640 committed bytes；
- 76 同区域 commits，13 跨区域 commits；
- tick 120 有 85 个活跃 transferred roots；
- effective transferred roots 为 84.0455；
- 暂无根同时跨多个区域存活。

短样本中稀缺与新文化根建立、凝聚度与同区域留存出现正相关，但只有 6 个窗口，不能外推为长期机制。
