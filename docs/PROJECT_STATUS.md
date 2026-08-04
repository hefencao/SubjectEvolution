# SubjectEvolution 当前项目状态

版本：**0.160.0**

## 当前迭代身份

- 进度类型：**`[MAIN-EXP]` 主线实验**
- Git 标题：**`[MAIN-EXP] D1-Z: decompose action-logit and CDF boundary pressure sources`**
- Git 分支：**`main-exp/stage3c41-pressure-source-decomposition`**
- 工作流档位：**`SCIENTIFIC-FREEZE` + `RELEASE-HANDOFF`**
- 当前冻结科学前沿：**Stage 3C-41**
- 下一项工程边界：**语义中立 Subject VM activation contribution trace**

## 类型化任务进度树

```text
SubjectEvolution
├── [MAIN-EXP] 主线实验
│   └── D1-Z 统一 Subject Graph VM
│       ├── [FROZEN] Stage 3C-40 精确 categorical action-boundary opportunity
│       ├── [FROZEN] Stage 3C-41 action-logit/CDF pressure source 分解
│       ├── [BLOCKED] Stage 3C-42 source-history→activation→REST output 因果分解
│       └── [BLOCKED] retention、learned weight 与 topology evolution
├── [BRANCH-EXP] 分支实验
│   └── 当前无活动项
├── [PARAM-EXP] 代码参数探索
│   └── 当前无活动项
├── [EVOLVE-ENV] 环境/底物演化代码
│   └── [PARKED] 持续多压力环境与 source-health 工作
├── [EVOLVE-SUBJECT] 主体能力演化代码
│   └── [BLOCKED] topology/readout/addressing evolution 尚无完整合同
├── [ENGINEERING] 运行时、工具、测试与打包
│   ├── [DONE] 语义中立 categorical sampling trace
│   ├── [NEXT] 语义中立 Subject VM activation contribution trace
│   └── [PARKED] 自动判断本地处理与 artifact handoff 意图
└── [DOC-GOV] 文档治理
    └── [DONE] 活动规范文档为中文权威文本
```

## 当前冻结判断

Stage 3C-41 在 Stage 3C-40 已冻结的每 source top-five boundary opportunity 上完成逐 action 分解。90 个事件、180 个 alignment mode comparison 中，130 个非零 masked-logit 变化全部只发生在 `REST` action port；其他 action 的概率变化全部来自 softmax 归一化后的质量重分配。

六个 realized crossing mode-event 中，`REST` logit 正变化与负变化各三次；五次存在其他 action probability 的净抵消，两次发生原最近端点与 extended active endpoint 的切换。非 crossing 事件的最大 `|REST logit delta|` 和 `|REST probability delta|` 都高于 crossing 最大值，因此符号或幅度不能单独解释 crossing。

`REST` 是当前 fixed bootstrap graph 的输出 action port，不具有价值语义。当前仍未解释 source history 如何通过 graph activation 产生不同符号和幅度的 `REST` output。

## 下一边界约束

下一项必须标记为 `[ENGINEERING]`，导出语义中立的 Subject VM activation contribution trace，至少记录 node activation、edge transmission、output gate contribution、temporary-write lineage 与 action-port aggregation，并证明 trace 开关不改变 action、RNG、checkpoint state 或 branch identity。完成该门前不得启动 Stage 3C-42。

## 文档与证据索引

| 需求 | 权威位置 |
|---|---|
| 项目使命与解释边界 | `docs/PROJECT_CHARTER.md` |
| 当前架构 | `docs/ARCHITECTURE.md` |
| Subject VM 机制合同 | `docs/PARTITIONED_SUBJECT_GRAPH_VM.md` |
| 当前科学问题 | `docs/SCIENTIFIC_ISSUES.md` |
| Stage 3C 冻结结果 | `docs/results/SUBJECT_VM_STAGE3C_RESULTS.md` |
| Stage 3C-41 决策 | `protocols/decisions/subject_graph_vm_stage3c41_pressure_source_v1.json` |
| 当前迭代记录 | `docs/迭代/v0.160_D1-Z_主体图Stage3C41_action-logit与CDF压力来源分解.md` |
