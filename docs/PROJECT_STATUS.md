# SubjectEvolution 当前项目状态

版本：**0.162.0**

## 当前迭代身份

- 进度类型：**`[MAIN-EXP]` 主线实验**
- Git 标题：**`[MAIN-EXP] D1-Z: audit activation contribution sources of REST output`**
- Git 分支：**`main-exp/stage3c42-rest-activation-source-audit`**
- 工作流档位：**`SCIENTIFIC-FREEZE` + `RELEASE-HANDOFF`**
- 当前冻结科学前沿：**Stage 3C-42**
- 下一项项目边界：**`[EVOLVE-SUBJECT]` 统一 ThoughtEvent/思维链底层实现**

## 类型化任务进度树

```text
SubjectEvolution
├── [MAIN-EXP] 主线实验
│   └── D1-Z 统一 Subject Graph VM
│       ├── [FROZEN] Stage 3C-40 精确 categorical action-boundary opportunity
│       ├── [FROZEN] Stage 3C-41 action-logit/CDF pressure source 分解
│       ├── [FROZEN] Stage 3C-42 REST activation contribution 来源审计
│       └── [OPEN] SG-09 上游 history/association/modulation→temporary-write proposal 来源
├── [BRANCH-EXP] 分支实验
│   └── [PARKED] 低代价/低扰动 action 的独立行为合同；不得与当前 action 集合混入
├── [PARAM-EXP] 代码参数探索
│   └── 当前无活动项
├── [EVOLVE-ENV] 环境/底物演化代码
│   └── [PARKED] 持续多压力环境与 source-health 工作
├── [EVOLVE-SUBJECT] 主体能力演化代码
│   ├── [NEXT] 统一 ThoughtEvent 表示与有界短暂思维链底层
│   ├── [CONSTRAINT] 不增加独立 RETHINK action
│   ├── [CONSTRAINT] 短期链与较长期记忆不得使用两种 token 表示
│   └── [BLOCKED] topology/readout/addressing evolution 尚无完整合同
├── [ENGINEERING] 运行时、工具、测试与打包
│   ├── [DONE] 语义中立 categorical sampling trace
│   ├── [DONE] 语义中立 Subject VM activation contribution trace
│   └── [PARKED] 自动判断本地处理与 artifact handoff 意图
└── [DOC-GOV] 文档治理
    └── [DONE] 活动规范文档为中文权威文本
```

## 本轮科学冻结判断

Stage 3C-42 只分析 Stage 3C-40 已冻结的 reference crossing source `12305、12308`、alignment-common source `12307` 和 replication 最高 opportunity source `12401`。每个 source 固定使用 top-five event identity，共 20 个事件、40 个 aligned/ablated mode-event。

结果表明：

- 40 个 mode-event 的 REST output exposure DID 均可由 activation trace 精确重建；
- 28 个 mode-event 具有非零 REST output DID；
- 所有已观测 active temporary-write target 都是 recurrent edge 0 的 `edge-forward-gate`；
- exposure DID 的结构贡献全部来自**当前 edge gate**；
- inherited node-state、state×gate interaction、input、bias 与 output-gate 的 DID 均为零；
- 六个 crossing 的绝对 gate contribution 为 `0.038269…0.122056`；
- noncrossing 的最大绝对 gate contribution 为 `0.167758`，因此 gate 变化幅度不能单独区分 crossing；
- seed `12307` 两种 alignment mode 的 gate contribution 几乎相同，符合 alignment-common crossing；
- seed `12401` 最高 opportunity 的 gate contribution 为 `0.082322`，但 categorical pressure/余量比仍只有 `0.688482`。

该结果解析的是 fixed bootstrap 的执行路径：

```text
active temporary edge-forward-gate write
→ delay-one recurrent self-edge transmission
→ linear node-0 accumulator
→ REST output gate
```

它没有解释 association/modulation 为什么提出该 gate write，也不把执行贡献升级为 causal attribution、value 或 credit quality。

## 暂停的 action 方案

`NO_ACTION` 不进入当前设计。低代价/低扰动 action 可能更符合现有行为系统，但会改变生态成本、action competition 与 sampling boundary，继续保持 `PARKED`，未来只能使用独立 `[BRANCH-EXP]` 或 `[EVOLVE-SUBJECT]` 合同。

思维链不依赖单独 `RETHINK` action。下一轮先实现内部状态与 ThoughtEvent 的递归/召回底层，让旧思考与新信息能够共同参与后续 activation，再独立判断是否需要任何额外行为类型。

## 下一边界约束

下一轮开始 `[EVOLVE-SUBJECT]` 思维链实现，但首个实现边界必须满足：

- 思维链 token 与较长期记忆 token 使用同一 ThoughtEvent 表示和 identity；
- 短期与长期的差异只允许体现在生命周期、索引与访问成本，不得依赖固定转译形成两套表示；
- `node_state` 负责当前连续计算，ThoughtEvent 负责可重新寻址的历史思考片段；
- 不增加独立 `RETHINK` action；
- 不把 action logits、Objective-Fact 或价值式汇总无条件回灌为 thought；
- 新机制必须默认关闭、具有成本与消融合同，并保持当前 Stage 3C bootstrap 结果可重现；
- 本轮 Stage 3C-42 结果不得作为 retention、reward 或 learned-weight 授权。

## 文档与证据索引

| 需求 | 权威位置 |
|---|---|
| 项目使命与解释边界 | `docs/PROJECT_CHARTER.md` |
| 当前架构 | `docs/ARCHITECTURE.md` |
| Subject VM 机制合同 | `docs/PARTITIONED_SUBJECT_GRAPH_VM.md` |
| 当前科学问题 | `docs/SCIENTIFIC_ISSUES.md` |
| Stage 3C 冻结结果 | `docs/results/SUBJECT_VM_STAGE3C_RESULTS.md` |
| Stage 3C-42 决策 | `protocols/decisions/subject_graph_vm_stage3c42_activation_source_v1.json` |
| 当前迭代记录 | `docs/迭代/v0.162_Stage3C42_REST_activation来源审计.md` |
