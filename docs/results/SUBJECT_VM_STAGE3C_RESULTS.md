# Subject VM Stage 3C 冻结结果台账

## 范围

本文档只保存简明且已验证的 Stage 3C 结论。它是历史证据，不是当前架构，也不是活动任务队列。详细 protocol 位于 `protocols/decisions/`；可执行 workflow 位于 `studies/`；当前工作位于 `docs/PROJECT_STATUS.md`。

表格中的**类型**是任务/进度类型，不是科学结果等级。

## Stage 3C-1 至 3C-16：基础设施链

| 范围 | 类型 | 冻结边界 |
|---|---|---|
| 3C-1–3C-3 | `[MAIN-EXP]` 工程实验 | 在 live write 前明确 exact target binding、bounded safe delta、atomic shadow transaction、compare-and-swap 与 rollback。 |
| 3C-4–3C-6 | `[MAIN-EXP]` 配对实验 | 建立 guarded temporary live write、无 score 的 21 坐标证据、共享 checkpoint branch identity 与 paired export。 |
| 3C-7–3C-9 | `[MAIN-EXP]` 证据基础设施 | 建立 integrity screen、source-balanced component reproducibility、fixed-bootstrap 短程 runner、对称 control reservation 与 export-boundary finalization。 |
| 3C-10–3C-13 | `[MAIN-EXP]` 诊断链 | 分开 update visibility、独立 source 充分性、branch-horizon coverage 与 temporary-exposure adequacy；稀疏下游事实没有被升级为 learning 结论。 |
| 3C-14–3C-16 | `[MAIN-EXP]` 可达性链 | 审计 parameter-family、local-sensitivity 与 eligibility-carrier reachability，但不把可达性解释为 causal-credit 质量。 |

## Stage 3C-17 至 3C-37

| Stage | 类型 | 受控变化 | 冻结结论 | 未授权解释 |
|---|---|---|---|---|
| 3C-17 | `[BRANCH-EXP]` | exact-similarity tie 时比较 latest 与 oldest。 | tie-break 显著改变 delay、历史复用、proposal 数和完成窗口；两臂都没有产生稳定 Objective-Fact 坐标。 | 声称 recency 有价值，或把某一臂选为科学上更优。 |
| 3C-18 | `[BRANCH-EXP]` | 固定 update budget，candidate limit 比较 1 与 2。 | Top-2 改变复用和漏斗计数，但没有扩大 unique historical identity coverage，也没有形成稳定下游事实。 | 把更多引用解释为更好的 credit。 |
| 3C-19 | `[MAIN-EXP]` 只读 | 重建 visible-token geometry。 | 活动可见向量严格恒为 `[0,0,1]`，content score 无法区分 candidate。 | 推广为 continuous token 普遍失败。 |
| 3C-20 | `[BRANCH-EXP]` | 增加一个共享 action-state readout。 | geometry 变为 rank one 且 tie 消失，但该坐标是共享时间相位，不是 subject/event identity。 | 把相位分离解释为历史理解。 |
| 3C-21 | `[BRANCH-EXP]` | 在共同支持上比较 constant-one 与 uncertainty-mean objective readout。 | subject/event-specific geometry 可达，但 selected historical identity coverage 下降，且下游事实仍不稳定。 | 给 uncertainty 赋价值。 |
| 3C-22 | `[MAIN-EXP]` 只读 | 重建完整 eligible 与 selected event set。 | candidate opportunity 不变；新 geometry 改变排序，并严格复用 eligible identity 的一个子集。 | 把 ranking coverage 或 reuse 解释为好坏。 |
| 3C-23 | `[BRANCH-EXP]` | 在共同 graph support 上增加第二 readout coordinate。 | 不改变 action output 时可得到 rank-two visible geometry；没有出现稳定 Objective-Fact 坐标。 | 声称 credit 得到改善。 |
| 3C-24 | `[MAIN-EXP]` 只读 | 重建 rank-two opportunity、winner 与 margin。 | exact tie 被移除，但 historical identity coverage 仍有界，winner margin 可能很小。 | 把非 tie score 等同于更强证据。 |
| 3C-25 | `[MAIN-EXP]` 只读 | 比较 winner reuse、normalized margin 与 opportunity。 | reused winner 不能仅由最小 margin 解释，并出现在不同 query vector 中。 | 把 reuse 解释为持续价值。 |
| 3C-26 | `[MAIN-EXP]` 只读 | 去除 source-boundary forced assignment，并按 age opportunity 归一化。 | age-one occupancy 在去除边界强制后仍存在；raw opportunity count 不能完全解释 reuse。 | 增加 age penalty 或随机分配。 |
| 3C-27 | `[MAIN-EXP]` 只读 | visible-token trajectory kinematics。 | 在冻结的 `1e-8` 诊断 bin 下，387 个 multi-candidate age-one selection 中 386 个 strict、1 个 near-tie；Stage 3C-37 后续证明该分箱案例在 runtime 语义下仍有严格正 margin。 | 把结果解释为 recency value。 |
| 3C-28 | `[MAIN-EXP]` 只读 | 离散状态与 recurrent-basin 审计。 | 第一坐标状态跨主体共享，第二坐标具有强 subject anchor；same-state winner 富集，但不存在 exact token replay。 | 声称 global phase 或 exact memory。 |
| 3C-29 | `[MAIN-EXP]` 只读 | 在 current-state opportunity 条件下分析 transition occupancy。 | 表面 transition-match enrichment 基本消失；在所有可比较情况下，same-state candidate 中第二坐标最近者获胜。 | 声称 transition replay。 |
| 3C-30 | `[PARAM-EXP]` 只读 scale panel | 第二坐标权重 `0, 0.1…10`。 | 权重为 0 会改变 winner identity，但不改变 state basin；所有正权重都保持最近第二坐标排序。 | 声称精调最优点或 learned weight。 |
| 3C-31 | `[MAIN-EXP]` 只读消融 | 保持坐标边际分布，同时打断 subject-time binding。 | same-state query 中 39.53%–74.51% 的 winner identity 改变；9 个 fact 坐标的局部匹配一致变差，但完整向量方向混合。 | 声称 scalar value 或正确 credit。 |
| 3C-32 | `[MAIN-EXP]` 四臂 runtime intervention | aligned/ablated × guarded-live/read-only-control。 | alignment 在每个 source 中都改变 selector identity 和 temporary update route；3-tick exposure 下没有形成稳定下游事实。 | 用内部路由因果性替代下游价值证据。 |
| 3C-33 | `[MAIN-EXP]` 匹配 horizon 干预 | 比较 `3/8`、`3/11`、`6/11` exposure/horizon。 | ledger dose 精确翻倍。固定支持轨迹效应只在 seed 12305 与 12308 变化；9 个 source 中没有稳定 signed 或 absolute fact coordinate。 | 自适应延长 exposure，或授权 retention、reward、learned weighting。 |
| 3C-34 | `[MAIN-EXP]` 只读 crossing audit | 复用 8 个 matched-horizon arm，将 exposure×alignment 差异定位到 action potential、sampled action、Objective-Fact event 与 aggregation。 | 9/9 source 都存在连续 Subject VM 决策差异；只有 12305、12308 出现 alignment-specific sampled-action crossing，随后产生 12 个 differential Objective-Fact event，且恰好复现 Stage 3C-33 的两个非零 source。12307 出现 alignment-common crossing，被 cross-mode contrast 消去。 | 声称精确数值 threshold margin、value、correct credit、keep/revert、learning 或 retention。 |
| 3C-35 | `[MAIN-EXP]` 独立 source 资格 | 在测试预注册 crossing classifier 前，用 seed 12401–12409 重建冻结 rank-two 链。 | panel 未通过历史 Stage 3C-27 geometry prerequisite：strict age-one geometry 从 386/387 降至 363/369，记录的 latest-tie use 从 1/864 升至 6/864。未运行 Stage 3C-28 及以后阶段；crossing 预测仍未测试。 | 替换 seed、放宽 gate、提出 crossing/value/learning/retention 结论。 |
| 3C-36 | `[MAIN-EXP]` 只读 transport decomposition | 比较原 panel 与独立 panel 的冻结 Stage 3C-25–27 输出。 | candidate support 和 winner reuse 精确迁移；age-one occupancy 下降由 first-state recurrence composition 预测；5 个额外 near-exact tie 直接触发形式 gate。local-step scale separation 仍约 200×。 | 把聚合 tie 计数当作机制已解析，修改 tolerance 或恢复 crossing replication。 |
| 3C-37 | `[MAIN-EXP]` 只读 selector audit | 重放两个冻结 rank-two panel，按存储坐标与真实 runtime ordering 解析所有 Stage 3C-27 near-tie query。 | 7 个 `1e-8` 诊断案例都有严格正的 float64 age-one margin（`4.42e-9`–`7.37e-9`），normalized direction 不同，第二坐标相差 1715–2140 个 float32 ULP。runtime `1e-12` comparator 在 1728 个 multi-candidate query 中判定 0 个 tie，latest-on-tie 未改变任何 winner。两个 panel 的 selector-consistent strict fraction 都为 1.0。 | 改写历史产物、修改 runtime tie 语义，或把资格修正当作 crossing replication。 |

## 当前冻结链

seed `12301–12309` 上的 Stage 3C-23→34 结果继续冻结。Stage 3C-35 之所以停止独立 panel，是因为历史 Stage 3C-27 分析把 7 个小但严格为正的 margin 归入 `1e-8` near-tie 类别，并将该类别描述为 latest-tie use。Stage 3C-37 证明它们都不是 runtime tie：实际 selector 使用 float64 score 和 `1e-12` comparator，latest-on-tie 没有改变 winner。

因此 Stage 3C-34 crossing 预测仍是“未测试”，不是“被反驳”或“已获得资格支持”。独立 panel 只能通过明确的 Stage 3C-37 selector-consistent qualification overlay 继续；历史 checksum-bound 产物保持不变。

## 下一项获授权的证据边界

Stage 3C-38 可以在 seed `12401–12409` 上，使用冻结 runtime 和 Stage 3C-37 qualification overlay，执行预注册的 Stage 3C-28 至 crossing-replication 链。

不得挑选 source，不得改变 exposure、addressing、horizon、crossing definition 或 runtime score comparison，也不得把“零阳性 panel”解释为非空复现支持。
