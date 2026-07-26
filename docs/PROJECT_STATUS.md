# Subject Evolution 项目状态

版本：**0.29.0**

## 本轮输入与结论

用户提供的 `analyses.zip` 包含三组完整的 v0.28 event-timed 结果：

| 批次 | Anchors | Eligible pairs | Pairing failures |
|---|---:|---:|---:|
| primary mechanisms | 18 | 54 | 0 |
| crowding knowledge mechanisms | 6 | 18 | 0 |
| mortality/scarcity knowledge mechanisms | 12 | 36 | 0 |
| **合计** | **18 unique** | **108/108** | **0** |

全部 branch 使用 `anchor-event-tick-v1`，baseline/intervention 在 event alive、全局 stable-ID hash 与区域 stable-ID hash 上一致。结果支持以下有限结论：

1. `disable-knowledge-transfer` 在 crowding、mortality、scarcity 中均减少区域 active transferred roots 和新传播活动，属于跨事件重复的文化状态维持作用；不等于人口、适应度或主体性收益。
2. `freeze-group-refresh` 对 current-label cohesion 的方向主要由标签评价边界变化产生；checkpoint-common cohesion 没有跨 seed、跨事件稳定方向。
3. `disable-knowledge-policy`、`ablate-working-memory`、`bypass-sparse-selection` 及资源亲和消融的下游方向依赖事件类型；现有结果不足以修改默认机制或参数。

v0.29 因此没有新增世界规则，而是将 group label、区域划分和 anchor selection 明确版本化并写入 provenance。

## v0.29 新增能力

### Group-label protocol

- schema：`trusted-directed-fixed-round-min-label-v1`；
- edge：目标 alive 且 materialized trust 达到阈值的有向关系槽；
- propagation：物理槽位标签初始化，固定轮数最小标签传播；
- group token：传播根槽位上的 stable entity ID；
- minimum size：不足最小成员数的组件保持未分组；
- flagship：threshold `0.12`、rounds `8`、minimum members `6`；
- refresh 与 label propagation 分层：旗舰使用 `adaptive-topology-v1`，最短 100、最长 300 ticks。

该协议是候选群组测量，不是精确无向连通分量，也不是主体存在判定。

### Spatial-region protocol

- schema：`normalized-fixed-count-grid-v1`；
- normalized equal-area rectangular partition；
- row-major-y-then-x region IDs；
- 发布物理区域宽高、world-cell 覆盖、对齐状态、topology/partition SHA-256；
- 4×4 区域在 128×128 地图上每区 32×32 物理单位；若地图变大而区域数不变，物理区域面积同步变大；
- manifest 默认拒绝混合不同物理区域几何，显式 override 才能继续。

### Anchor-selection protocol

- 当前新 manifest schema：`natural-event-paired-intervention-matrix-v2`；
- selection schema：`exposure-only-local-peak-selection-v2`；
- 每个区域自己的 80% exposure 分位阈值；
- 内部局部峰、区域内最小间隔、区域内 z-score 排序；
- 优先不同区域，再按 z-score 降序、tick 升序、region ID 升序；
- 最新严格早于 event tick 的完整 checkpoint；
- 选择过程不读取事后 outcome；
- z-score 不可跨事件类型解释为统一强度。

### Protocol audit 与长期分析

- 新增 `subject_evolution.protocol_audit`；
- run manifest、run metadata、scientific validity、local diagnostics 和 event cohort 发布协议字段与哈希；
- long-run analysis 升级为 `multi-seed-long-run-analysis-v8`；
- 旧 v1 natural-event manifest 继续可读取，缺失的新字段会标记为 legacy/inferred，而不是伪造物理几何。

## 当前实现矩阵

| 领域 | 状态 | 边界 |
|---|---|---|
| CPU reference | 完成 | 当前科学语义权威 |
| GPU strict-reference | 完成 | 验证设备，执行 reference 世界 |
| GPU hybrid-accelerated | 部分完成 | 长程 parity 未证明 |
| 四资源异步生态位 | 完成 | 任意信息通道 schema 未完成 |
| 环境插件 ABI | 完成 | 非负标量场、默认关闭、无实体访问 |
| 实体/生命周期/谱系 | 完成 | 主要提交仍在 CPU |
| 遗传策略与 K1–K4 知识 | 完成 | 固定行动/特征 vocabulary 仍是模型约束 |
| L1/L2、路由成本、记忆、Top-k | 完成 | 均可 checkpoint 与消融 |
| 社会关系与 adaptive groups | 完成 | 候选主体结构，不是主体性判定 |
| group-label provenance | **v0.29 完成** | 有向、有限轮传播，不宣称精确组件 |
| spatial-region provenance | **v0.29 完成** | 固定归一化区域数，物理尺度随地图变化 |
| anchor-selection provenance | **v0.29 v2** | outcome-blind，自然峰值非随机 exposure |
| event-timed paired execution | 完成 | 108/108 用户结果 pairing 通过 |
| common boundary / event cohort | 完成 | 诊断层，不反馈世界 |
| result synthesis | 完成 | timing estimand 不可混合，seed-first 聚合 |
| 任意嵌套主体数据库 | 未完成 | 当前是候选图与摘要 |
| 主体性/主体偏移评分 | 未完成 | 不允许由单一代理推出 |
| Hero RL、多 GPU | 未完成 | 当前非科学优先级 |

## 当前科学解释

1. 传播在共同 event state 后维持短期局部文化状态；没有证明其人口收益。
2. 群组刷新消融的 current-label cohesion 受定义耦合，必须优先 common-boundary 口径。
3. 区域人口由留存、迁出、缺失、既有实体迁入和事件后出生共同构成；方向依赖事件类型。
4. 两个 anchors/seed 先在 seed 内平均，不能当作六个独立重复。
5. 区域、群组与 anchor 都是测量协议；改变协议必须产生新 schema/hash，不能静默改义。

## 验证

- 全量测试：`136 passed, 1 skipped`；
- 新测试覆盖固定传播轮数的可达范围差异、地图尺寸下 topology/partition hash 分离、manifest 混合几何拒绝和 protocol audit；
- 默认世界兼容与 trusted checkpoint 恢复报告位于 `docs/v0.29/`；
- 默认动力学未因协议 provenance 改变。

## 下一阶段

1. 使用 v2 manifest 对至少两种地图物理尺寸或 region count 做**预注册尺度敏感性实验**，不直接池化不同 partition hash；
2. 对 group label 的 rounds、threshold、minimum members 做诊断敏感性矩阵，保持世界轨迹不变并报告候选群组稳定性；
3. 仅在上述测量稳健性成立后，才讨论社会候选结构的跨尺度解释；
4. 任意信息通道 schema 与真实 CUDA hybrid parity 继续作为独立工程主线。
