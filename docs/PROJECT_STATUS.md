# SubjectEvolution 当前项目状态

版本：**0.165.0**

## 当前迭代身份

- 进度类型：**`[BRANCH-EXP]` 分支实验**
- Git 标题：**`[BRANCH-EXP] subject-vm: audit pre-recall ThoughtEvent degeneration`**
- Git 分支：**`branch-exp/thought-event-t2-degeneration`**
- 工作流档位：**`SCIENTIFIC-FREEZE` + `RELEASE-HANDOFF`**
- 当前冻结科学前沿：**Stage 3C-42**
- 当前完成边界：**T2 前向 recall 前 ThoughtEvent 退化审计**
- 下一项项目边界：**T3 最小前向 recall 机制 smoke**

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
│   ├── [NEXT] T3：最小前向 recall 机制 smoke
│   ├── [PARKED] 低代价/低扰动 action
│   └── [PARKED] read-head diversity、temperature 与 retrieval-role 对照
├── [PARAM-EXP] 代码参数探索
│   └── 当前无活动项
├── [EVOLVE-ENV] 环境/底物演化代码
│   ├── [PARKED] 持续多压力环境与 source-health
│   └── [OPEN] 非对称可观测与因子化语言资格环境
├── [EVOLVE-SUBJECT] 主体能力演化代码
│   ├── [DONE] T1：统一 ThoughtEvent schema、identity、parent DAG 与 bounded arena
│   ├── [QUALIFIED] T3：仅允许最小前向 recall 机制 smoke
│   ├── [BLOCKED] 分布式思维链资格与回声治理
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

## T2 冻结边界

T2 使用 9 个新 seed（12501～12509）、16 个稳定主体和 12 tick 审计窗口，对比两条 action-identical 只读臂：

- `duplicate-coordinate-control`：thought readout 使用 `port 11 + port 11`；
- `rank-two-candidate`：thought readout 使用 `port 11 + port 7`。

两臂的 event identity、action、sampled probability 和 action potentials 完全一致，只允许 token coordinate 30 不同。

冻结结果：

- 负对照每 seed centered rank 均为 1，精确重复比例为 95.83%～98.44%；
- rank-two 候选每 seed 192/192 个事件精确不同，centered rank 均为 2；
- rank-two 候选连续同主体 token 的 cosine 中位数为 0.999049～0.999097；
- 每 arm/seed 均为 192 次 emission、48 次 expiry、0 次 overwrite、144 个最终保留事件；
- runtime parent_count 保持 0。

因此 T1 arena 和退化诊断获得资格，但当前 fixed bootstrap 仍是低秩、高局部相似的工程表示。T2 不支持“已形成思维链”“已形成分布式认知表示”或“已形成语言”。

## 下一实现边界

T3 只允许最小机制 smoke：

- 单一、无固定认知角色的只读路径；
- 只读取前一 tick 以前已提交的 ThoughtEvent；
- parent DAG 记录真实 recalled parent；
- 与无 recall、token 内容打乱及等成本 control 比较；
- 保持 action、Objective-Fact、reward、confidence 与语言边界隔离；
- 不授权 retention、multi-head、temperature、novelty route 或永久写入。

T3 的目的只是证明 recalled ThoughtEvent 能以有界、可审计且非退化的方式进入统一图，并不证明思维链已经出现。

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
| 当前迭代记录 | `docs/迭代/v0.165_ThoughtEvent_T2退化审计.md` |
