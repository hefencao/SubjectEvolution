# SubjectEvolution 当前项目状态

版本：**0.163.0**

## 当前迭代身份

- 进度类型：**`[DOC-GOV]` 文档治理**
- Git 标题：**`[DOC-GOV] subject cognition: formalize ThoughtEvent and language boundaries`**
- Git 分支：**`docs/thought-language-research-boundaries`**
- 工作流档位：**`SCOPED-FIX` + `RELEASE-HANDOFF`**
- 当前冻结科学前沿：**Stage 3C-42**
- 下一项项目边界：**`[EVOLVE-SUBJECT]` T1 统一 ThoughtEvent 基础设施**

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
│   ├── [PARKED] 低代价/低扰动 action
│   └── [PARKED] read-head diversity、temperature 与 retrieval-role 对照
├── [PARAM-EXP] 代码参数探索
│   └── 当前无活动项
├── [EVOLVE-ENV] 环境/底物演化代码
│   ├── [PARKED] 持续多压力环境与 source-health
│   └── [OPEN] 非对称可观测与因子化语言资格环境
├── [EVOLVE-SUBJECT] 主体能力演化代码
│   ├── [NEXT] T1：统一 ThoughtEvent schema、identity、parent DAG 与 bounded arena
│   ├── [BLOCKED] T2：ThoughtEvent 退化与 lineage 审计
│   ├── [BLOCKED] T3：最小前向 recall
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

## 下一实现边界

下一轮只实现 T1 基础设施：

- 统一 ThoughtEvent vector 与稳定 event identity；
- parent DAG 与 source/configuration/branch/checkpoint lineage；
- 有界 arena、lifecycle metadata 与明确回收；
- checkpoint、clone、branch identity 和成本计量；
- 默认关闭，并保持 Stage 3C bootstrap 可重现。

下一轮不实现：

- 独立 `RETHINK`、`NO_ACTION` 或 confidence gate；
- 前向 read head/recall；
- 长期 retention policy；
- communication interface、语言环境或世界频道；
- 短期 thought 与 memory thought 两套表示；
- Objective-Fact、action logits 或价值式摘要的无条件回灌。

## 语言与跨世界研究边界

- communication region 只作为统一图与物理 SignalEvent channel 的接口，不拥有词义或语言认知；
- 共享信号约定、对象指称、组合语言和内部认知复用必须分层资格化；
- 不同 seed/区域的同一对象允许使用不同 signal、node、topology 和 region 分布；
- 比较必须对齐功能、指称分区、关系结构与反事实干预，不能硬对齐词形或 node ID；
- “类似哈夫曼编码”只登记为成本约束编码同态假设，不预设 prefix-free、无损、离散或最优；
- 观察者的原生语言干预必须通过同一物理频道，不能直接写入主体内部概念。

## 暂停的 action 方案

`NO_ACTION` 不采用；独立 `RETHINK` 当前没有必要。低代价/低扰动 action 继续保持 `PARKED`，未来必须在独立行为合同中处理成本、物理效果和 action competition。

## 文档与证据索引

| 需求 | 权威位置 |
|---|---|
| 项目使命与解释边界 | `docs/PROJECT_CHARTER.md` |
| 当前架构 | `docs/ARCHITECTURE.md` |
| Subject VM 当前机制 | `docs/PARTITIONED_SUBJECT_GRAPH_VM.md` |
| ThoughtEvent、思维链与语言设计 | `docs/THOUGHT_EVENT_LANGUAGE_COGNITION.md` |
| 当前科学问题 | `docs/SCIENTIFIC_ISSUES.md` |
| Stage 3C 冻结结果 | `docs/results/SUBJECT_VM_STAGE3C_RESULTS.md` |
| 上一科学迭代记录 | `docs/迭代/v0.162_Stage3C42_REST_activation来源审计.md` |
| 当前文档治理记录 | `docs/迭代/v0.163_思维链与语言认知设计治理.md` |
