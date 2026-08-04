# SubjectEvolution 当前项目状态

版本：**0.166.0**

## 当前迭代身份

- 进度类型：**`[EVOLVE-SUBJECT]` 主体能力演化代码**
- Git 标题：**`[EVOLVE-SUBJECT] subject-vm: introduce minimal forward ThoughtEvent recall`**
- Git 分支：**`evolve-subject/thought-event-t3-recall`**
- 工作流档位：**`SCIENTIFIC-FREEZE` + `RELEASE-HANDOFF`**
- 当前冻结科学前沿：**Stage 3C-42**
- 当前完成边界：**T3 最小前向 ThoughtEvent recall 机制 smoke**
- 下一项项目边界：**T4 延迟信息效用与 lineage echo 只读审计**

## 类型化任务进度树

```text
SubjectEvolution
├── [MAIN-EXP] 主线实验
│   └── D1-Z 统一 Subject Graph VM
│       ├── [FROZEN] Stage 3C-40 精确 categorical boundary
│       ├── [FROZEN] Stage 3C-41 action-logit/CDF pressure source
│       ├── [FROZEN] Stage 3C-42 REST activation contribution source
│       └── [OPEN] SG-09 history/association/modulation→temporary-write proposal
├── [BRANCH-EXP] 分支实验
│   ├── [DONE] T2：前向 recall 前 ThoughtEvent 退化审计
│   ├── [NEXT] T4：延迟信息效用与 lineage echo 审计
│   ├── [PARKED] 低代价/低扰动 action
│   └── [BLOCKED] multi-head、temperature、retrieval-role 与 retention 对照
├── [PARAM-EXP] 代码参数探索
│   └── 当前无活动项
├── [EVOLVE-ENV] 环境/底物演化代码
│   ├── [PARKED] 持续多压力环境与 source-health
│   └── [OPEN] 非对称可观测与因子化语言资格环境
├── [EVOLVE-SUBJECT] 主体能力演化代码
│   ├── [DONE] T1：统一 ThoughtEvent schema、identity、parent DAG 与 bounded arena
│   ├── [DONE] T3：单一路径最近严格历史事件 recall 机制 smoke
│   ├── [QUALIFIED] T4：延迟信息效用与 lineage echo 只读审计
│   ├── [BLOCKED] 分布式思维链资格、多头读取与连续 retention
│   ├── [BLOCKED] communication interface 与 SignalEvent mapping
│   └── [BLOCKED] topology/readout/addressing evolution
├── [ENGINEERING] 运行时、工具、测试与打包
│   ├── [DONE] 语义中立 categorical sampling trace
│   ├── [DONE] 语义中立 activation contribution trace
│   └── [PARKED] 自动判断本地处理与 artifact handoff 意图
└── [DOC-GOV] 文档治理
    ├── [DONE] 活动规范文档为中文权威文本
    └── [DONE] ThoughtEvent、思维链、通信和语言研究合同
```

## T3 冻结边界

T3 使用 9 个新 seed（12601～12609）、16 个稳定主体和 10 tick 审计窗口，冻结四臂：

- `no-recall`：完全关闭 recall；
- `identity-recall`：读取最近一个严格早于当前 tick 的 ThoughtEvent 原内容；
- `rotate-one-coordinate-control`：parent identity、age 与成本相同，但循环置换 token coordinate；
- `zero-content-equal-cost-control`：selector、parent DAG 和计数成本相同，读入零内容。

Recall 只通过 fixed-bootstrap node 9 的 graph-defined ingress 进入 readout-only 路径；node 9 不拥有 action output。冻结结果：

- 每 enabled arm/seed 形成 144 条真实 parent link，16 个首事件为 root；
- 所有 parent 均严格来自前一 tick，未读取同 tick 新事件；
- identity、rotate 与 zero 三臂的搜索、读取、ingress 和 parent-link 计数成本完全一致；
- zero-content 与 no-recall 的 ThoughtEvent token 完全一致；
- identity 与 rotate 只改变 token coordinate 30，并可由 parent token 与 `0.25` ingress gate 重建；
- 最大重建残差为 `5.960464477539063e-08`；
- 四臂 event identity、action、sampled probability 与 action potentials 完全一致；
- identity parent-child cosine 的跨 seed 中位数范围为 `0.999081～0.999789`。

因此 T3 证明最小前向 recall、真实 parent DAG、等成本 control、checkpoint/clone 和 graph ingress 链路可以运行；但 fixed-bootstrap token 仍低秩且高度局部相似。T3 不证明延迟信息效用、思维链、分布式认知、语义记忆、语言或长期 retention。

## 下一实现边界

T4 只能在保持同一单一路径机制的前提下，审计：

- recall 是否携带当前 observation 中已缺失的延迟信息；
- identity recall 相对内容置换、零内容和 no-recall 是否具有内容特异效应；
- 最新事件链是否形成机械回声、lineage 垄断或 observation 压制；
- parent-child 加工是否只是 coordinate 30 的稳定自回灌；
- 使用相同成本预算时，下游信息与行为差异是否可复现。

T4 之前不得实现 multi-head、temperature、novelty/contrast role、reference-count retention、永久保留或语言接口。

## 语言与跨世界研究边界

- communication region 只作为统一图与物理 SignalEvent channel 的接口，不拥有词义或语言认知；
- 共享信号约定、对象指称、组合语言和内部认知复用必须分层资格化；
- 不同 seed/区域的同一对象允许使用不同 signal、node、topology 和 region 分布；
- 比较必须对齐功能、指称分区、关系结构与反事实干预，不能硬对齐词形或 node ID；
- “类似哈夫曼编码”只登记为成本约束编码同态假设。

## 暂停的 action 方案

`NO_ACTION` 不采用；独立 `RETHINK` 当前没有必要。低代价/低扰动 action 继续保持 `PARKED`。

## 文档与证据索引

| 需求 | 权威位置 |
|---|---|
| 项目使命与解释边界 | `docs/PROJECT_CHARTER.md` |
| 当前架构 | `docs/ARCHITECTURE.md` |
| Subject VM 当前机制 | `docs/PARTITIONED_SUBJECT_GRAPH_VM.md` |
| ThoughtEvent、思维链与语言设计 | `docs/THOUGHT_EVENT_LANGUAGE_COGNITION.md` |
| 当前科学问题 | `docs/SCIENTIFIC_ISSUES.md` |
| Stage 3C 冻结结果 | `docs/results/SUBJECT_VM_STAGE3C_RESULTS.md` |
| ThoughtEvent 冻结结果 | `docs/results/THOUGHT_EVENT_RESULTS.md` |
| 当前迭代记录 | `docs/迭代/v0.166_ThoughtEvent_T3最小前向recall.md` |
