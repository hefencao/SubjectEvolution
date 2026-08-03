# SubjectEvolution 当前项目状态

版本：**0.155.0**

## 当前迭代身份

- 进度类型：**`[DOC-GOV]` 中文权威文档统一**
- Git 标题：**`[DOC-GOV] docs: make active contracts Chinese-authoritative`**
- Git 分支：**`docs/v0.155-chinese-authoritative-contracts`**
- 工作流档位：**`SCOPED-FIX` + 版本化 `RELEASE-HANDOFF`**
- runtime/config/checkpoint 变化：**无**
- 当前冻结科学前沿：**Stage 3C-37**
- 下一项已授权主线实验：**Stage 3C-38，通过 selector-consistent qualification overlay 在独立 panel 上复现 crossing 分类**

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
│       ├── [NEXT]   Stage 3C-38 独立 panel crossing replication
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

Stage 3C-37 仍是最新冻结科学结果。它确认 Stage 3C-27 的七个 near-tie 都只是分析分箱结果，并非 runtime comparator 判定的 tie。按 selector 真实语义重新分类后，两个 source panel 都保留 strict bootstrap geometry，因此 Stage 3C-34 的 crossing 预测仍未在独立 panel 上测试。

本轮只改变活动文档的权威语言和术语表达，不改变上述证据、checksum 或 Stage 3C-38 的授权边界。

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
| 当前迭代记录 | `docs/迭代/v0.155_活动规范文档中文化.md` |
| 可执行 decision contract | `protocols/decisions/` |
| 仓库执行规则 | `AGENTS.md` |
