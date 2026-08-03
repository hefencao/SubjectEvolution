# SubjectEvolution 当前项目状态

版本：**0.157.0**

## 当前迭代身份

- 进度类型：**`[MAIN-EXP]` Stage 3C-39 跨 panel action-boundary opportunity 分解**
- Git 标题：**`[MAIN-EXP] D1-Z: audit action-boundary opportunity transport across panels`**
- Git 分支：**`main-exp/stage3c39-boundary-opportunity-transport`**
- 工作流档位：**`SCIENTIFIC-FREEZE` + `RELEASE-HANDOFF`**
- runtime/config/checkpoint 变化：**无**
- 当前冻结科学前沿：**Stage 3C-39**
- 下一项已授权任务：**`[ENGINEERING]` 语义中立的完整 masked policy logits 与 counter-based categorical draw 导出**

## 类型化任务进度树

```text
SubjectEvolution
├── [MAIN-EXP] 主线实验
│   └── D1-Z 统一 Subject Graph VM
│       ├── [FROZEN] Stage 3C-34 action / Objective-Fact crossing 审计
│       ├── [FROZEN] Stage 3C-38 独立 panel crossing replication：零阳性、仅 vacuous match
│       ├── [FROZEN] Stage 3C-39 action-boundary opportunity transport
│       ├── [BLOCKED] Stage 3C-40 精确 categorical boundary audit
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
│   └── [BLOCKED] topology/readout/addressing evolution 尚无 mutation、cost、development、inheritance 与 neutralization 合同
│
├── [ENGINEERING] 运行时、工具、测试与打包
│   ├── [NEXT] 语义中立导出完整 masked policy logits 与 counter-based categorical draw
│   ├── [DONE] `se-workspace` 管理项目外 result/patch 目录
│   └── [PARKED] 自动判断本地处理与 artifact handoff 意图
│
└── [DOC-GOV] 文档治理
    ├── [DONE] 活动文档职责分离
    └── [DONE] 活动规范文档统一为中文权威文本
```

## 当前主线判断

Stage 3C-39 比较了原 panel 与独立 panel 的冻结 Stage 3C-34 输出。两个 panel 的 continuous Subject VM divergence 在事件数、L1 幅度、tick 分布与已导出的同 action sampled probability 变化上大量重叠；独立 panel 并不整体更弱、更早或更缺少晚期差异。没有任何一个已观察的单调高阈值能把原 panel 的两个 crossing source 与全部非 crossing source 完全分开。

Stage 3C-36 已证明 candidate support 与局部 token 几何迁移，因此独立 panel 的零 crossing 不能归因于这些前置结构。first-state recurrence composition 确实变化，但现有事件级证据不能证明它导致零 crossing。剩余不确定性被收窄到当前冻结 trace 未记录的完整 categorical competition 与 counter-based draw state。

因此不得继续抽取 panel、延长 exposure 或调整 crossing threshold。下一项必须先作为 `[ENGINEERING]` 导出 instrumentation，证明 sampled action、random stream、checkpoint 与 branch identity 均不改变；Stage 3C-40 在该工程边界完成前保持阻塞。

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
| 当前迭代记录 | `docs/迭代/v0.157_D1-Z_主体图Stage3C39_动作边界机会迁移审计.md` |
| 可执行 decision contract | `protocols/decisions/` |
| 仓库执行规则 | `AGENTS.md` |
