# SubjectEvolution 当前项目状态

版本：**0.156.0**

## 当前迭代身份

- 进度类型：**`[MAIN-EXP]` Stage 3C-38 独立 panel crossing replication**
- Git 标题：**`[MAIN-EXP] D1-Z: replicate crossing classifier on qualified disjoint panel`**
- Git 分支：**`main-exp/stage3c38-disjoint-crossing-replication`**
- 工作流档位：**`SCIENTIFIC-FREEZE` + `RELEASE-HANDOFF`**
- runtime/config/checkpoint 变化：**无**
- 当前冻结科学前沿：**Stage 3C-38**
- 下一项已授权主线实验：**Stage 3C-39，跨 panel 分解 continuous divergence 到 sampled-action boundary 的机会差异**

## 类型化任务进度树

```text
SubjectEvolution
├── [MAIN-EXP] 主线实验
│   └── D1-Z 统一 Subject Graph VM
│       ├── [FROZEN] Stage 3C-33 匹配 horizon 的 exposure propagation
│       ├── [FROZEN] Stage 3C-34 action / Objective-Fact crossing 审计
│       ├── [FROZEN] Stage 3C-35 在历史诊断门下停止独立 panel
│       ├── [FROZEN] Stage 3C-36 bootstrap geometry 跨 panel 分解
│       ├── [FROZEN] Stage 3C-37 按 selector 真实语义解析 near-tie 来源
│       ├── [FROZEN] Stage 3C-38 独立 panel crossing replication：零阳性、仅 vacuous match
│       ├── [NEXT]   Stage 3C-39 跨 panel action-boundary opportunity 分解
│       └── [BLOCKED] retention、learned weight 与 topology evolution
│
├── [BRANCH-EXP] 分支实验
│   └── 当前无活动项
│
├── [PARAM-EXP] 代码参数探索
│   └── 当前无活动项
│
├── [EVOLVE-ENV] 环境/底物演化代码
│   └── [PARKED] 持续多压力环境与 source-health 工作
│
├── [EVOLVE-SUBJECT] 主体能力演化代码
│   └── [BLOCKED] topology/readout/addressing evolution 尚无获授权的
│       mutation、cost、development、inheritance 与 neutralization 合同
│
├── [ENGINEERING] 运行时、工具、测试与打包
│   ├── [DONE] `se-workspace` 管理项目外 result/patch 目录
│   ├── [PARKED] 自动判断本地处理与 artifact handoff 意图
│   └── [PARKED] 可选的完整 policy-logit 与 categorical-draw trace export
│
└── [DOC-GOV] 文档治理
    ├── [DONE] Architecture、Issues、Status 与 result ledger 职责分离
    ├── [DONE] Charter、Governance 与 Subject VM 当前合同整理
    └── [DONE] 活动规范文档统一为中文权威文本
```

## 当前主线判断

Stage 3C-38 在 seed `12401–12409` 上完成了 Stage 3C-37 qualification overlay 之后的完整 3C-28→34 链。九个 source 都产生 exposure-dependent、alignment-dependent 的连续 Subject VM potential divergence，但没有 source 跨越实际 sampled-action 边界，也没有 source 产生 exposure-only Objective-Fact effect。

因此 predictor 与 outcome 集合精确相等且都为空：分类器在独立 panel 上**未被反驳**，但只形成 vacuous match，不能计为非空复现支持。下一步不得继续增加随机 panel 来追逐阳性，而应只读比较原 panel 与独立 panel 的连续差异幅度、action composition 和可见 sampled probability，定位 crossing opportunity 为什么没有迁移；精确 categorical boundary margin 仍受 SG-07 的 trace 可观测性限制。

## 文档与证据索引

| 需求 | 权威位置 |
|---|---|
| 项目使命与解释边界 | `docs/PROJECT_CHARTER.md` |
| 长期治理与工作流规则 | `docs/PROJECT_GOVERNANCE.md`、`AGENTS.md` |
| 当前系统结构 | `docs/ARCHITECTURE.md` |
| 当前 Subject Graph VM 语义 | `docs/PARTITIONED_SUBJECT_GRAPH_VM.md` |
| 当前任务与队列 | `docs/PROJECT_STATUS.md` |
| 当前科学问题 | `docs/SCIENTIFIC_ISSUES.md` |
| 已冻结 Stage 3C 结果 | `docs/results/SUBJECT_VM_STAGE3C_RESULTS.md` |
| 当前迭代记录 | `docs/迭代/v0.156_D1-Z_主体图Stage3C38_独立Panel跨界分类复现.md` |
| 可执行 decision contract | `protocols/decisions/` |
| 仓库执行规则 | `AGENTS.md` |
