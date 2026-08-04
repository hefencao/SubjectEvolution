# ThoughtEvent 冻结结果台账

状态：**冻结结果台账**

本文档只记录已通过协议和发布验证的 ThoughtEvent 结果。设计讨论见 `docs/THOUGHT_EVENT_LANGUAGE_COGNITION.md`，活动问题见 `docs/SCIENTIFIC_ISSUES.md`。

## T1：统一 ThoughtEvent 基础设施（v0.164）

- 默认关闭的不可变 pre-action ThoughtEvent 核心；
- 同一 graph-produced token 与稳定 event identity；
- parent DAG schema、bounded per-subject arena 和硬 age ceiling；
- birth/death/compaction、checkpoint、clone 与 branch identity；
- emission、coordinate、parent-link 与 retention 计数成本；
- runtime parent_count 为 0，未实现前向 recall。

T1 是存储和身份基础设施，不构成思维链或记忆能力证据。

## T2：前向 recall 前退化审计（v0.165）

### 设计

- seeds：12501～12509；
- 每 seed 16 个稳定主体、12 个审计 tick；
- 每 arm/seed 192 个事件；
- `duplicate-coordinate-control`：`port 11 + port 11`；
- `rank-two-candidate`：`port 11 + port 7`；
- 两臂 event、action、sampled probability 与 action potentials 相同，只允许 token coordinate 30 不同。

### 冻结结果

| 指标 | 重复坐标负对照 | rank-two 候选 |
|---|---:|---:|
| centered numerical rank | 所有 seed 为 1 | 所有 seed 为 2 |
| 每 seed 精确唯一事件 | 3～8 | 192/192 |
| 精确重复比例 | 0.958333～0.984375 | 0 |
| stable rank | 1 | 1.132816～1.289768 |
| effective rank | 1 | 1.435334～1.703613 |
| 连续同主体 cosine 中位数 | 0.998263 | 0.999049～0.999097 |
| runtime parent_count | 0 | 0 |
| expiry / overwrite / final stored | 48 / 0 / 144 | 48 / 0 / 144 |

负对照证明退化诊断可以识别 rank-one collapse。rank-two 候选证明第二个独立只读坐标足以消除精确事件重复，但其变化仍限制在两个坐标和 rank-two 子空间，且跨 tick 局部相似度很高。

### 资格边界

授权：

- T1 arena 生命周期与事件身份；
- T2 退化诊断；
- T3 最小前向 recall 机制 smoke。

不授权：

- 已形成思维链；
- 已形成分布式认知表示；
- 语言或对象指称；
- reference count 表示有用性；
- retention 或永久记忆；
- 预设 read-head 角色。

冻结 assessment SHA-256：`fd553555909435de069067ea95c06baefa060e25a66d2de386be2c4e32374f7a`。

## T3：最小前向 ThoughtEvent recall（v0.166）

### 设计

- seeds：12601～12609；
- 每 seed 16 个稳定主体、10 个审计 tick；
- 每 arm/seed 160 个事件；
- selector：最近一个严格早于当前 tick 的 retained ThoughtEvent；
- 单一 graph ingress：node 9、token port 30、gate `0.25`；
- node 9 为 readout-only 节点，不拥有 action output；
- 四臂：`no-recall`、`identity-recall`、`rotate-one-coordinate-control`、`zero-content-equal-cost-control`。

### 冻结结果

| 合同 | 结果 |
|---|---:|
| 每 enabled arm/seed parent links | 144 |
| 每 enabled arm/seed root events | 16 |
| parent age | 全部为 1 tick |
| enabled 三臂计数成本 | 完全一致 |
| zero-content token 与 no-recall | 完全一致 |
| identity/rotate 改变的 token coordinate | 仅 30 |
| 最大 ingress 重建残差 | `5.960464477539063e-08` |
| event/action/probability/action potentials | 四臂完全一致 |
| identity parent-child cosine 中位数范围 | `0.999081～0.999789` |
| rotate parent-child cosine 中位数范围 | `0.999036～0.999309` |

T3 证明：统一 arena 中已提交的历史 ThoughtEvent 可以通过单一、确定性、无固定认知角色的 graph ingress 进入下一 tick activation；该 parent identity 会作为真实 parent DAG edge 记录，且内容效应能够与 selector、parent linkage 和计数成本分离。

### 资格边界

授权：

- 单一 latest-prior selector 与 graph ingress 机制；
- 真实 parent DAG；
- no-recall、内容置换和 zero-content 等成本 control；
- T4 延迟信息效用与 lineage echo 只读审计。

不授权：

- 已形成思维链；
- recall 已携带有用延迟信息；
- 已形成分布式认知或语义记忆；
- multi-head、temperature、固定 retrieval role；
- reference-count retention、永久保留；
- 语言、对象指称或通信接口。

冻结 assessment SHA-256：`30540e9d5d93b8987f042eef414b16eb6b28a435b997f4fecf95b81d7e9447dd`。
