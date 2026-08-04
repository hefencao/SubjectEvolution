# SubjectEvolution 当前项目状态

版本：**0.159.0**

## 当前迭代身份

- 进度类型：**`[MAIN-EXP]` 主线实验**
- Git 标题：**`[MAIN-EXP] D1-Z: audit exact categorical action-boundary opportunity`**
- Git 分支：**`main-exp/stage3c40-exact-categorical-boundary`**
- 工作流档位：**`SCIENTIFIC-FREEZE` + `RELEASE-HANDOFF`**
- 当前冻结科学前沿：**Stage 3C-40**
- 下一项已授权主线：**Stage 3C-41 action-logit/CDF pressure source 只读分解**

## 类型化任务进度树

```text
SubjectEvolution
├── [MAIN-EXP] 主线实验
│   └── D1-Z 统一 Subject Graph VM
│       ├── [FROZEN] Stage 3C-39 跨 panel action-boundary opportunity transport
│       ├── [FROZEN] Stage 3C-40 精确 categorical action-boundary opportunity
│       ├── [NEXT]   Stage 3C-41 action-logit/CDF pressure source 分解
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
│   └── [PARKED] 自动判断本地处理与 artifact handoff 意图
└── [DOC-GOV] 文档治理
    └── [DONE] 活动规范文档为中文权威文本
```

## 当前冻结判断

精确 categorical 边界由两个逐事件量决定：原 sampled action 的 CDF interval 到 uniform draw 的剩余余量，以及 exposure 延长造成的同一 interval 边界移动。边界移动耗尽原余量时才发生实际 crossing。

原 panel 的 crossing source 仍为 `12305、12308`；另有 `12307` 在两种 alignment 模式中发生相同 crossing，因而被 difference-in-differences 消去。独立 panel 的全部压力/余量比均小于 1，最大值为 `0.68848`，所以每个事件都保留正余量。

该结果解决“是否接近并跨越实际随机采样边界”的可观测性问题，但尚未解释不同 source history 为什么产生不同方向和幅度的 logit/CDF 边界压力。

## 下一主线约束

Stage 3C-41 只能读取现有 Stage 3C-40 trace，逐 action 分解 masked-logit、概率与 CDF endpoint 的变化来源。不得重跑新 panel、改变 exposure、修改 sampling kernel、拟合后见阈值或形成价值分数。

## 文档与证据索引

| 需求 | 权威位置 |
|---|---|
| 项目使命与解释边界 | `docs/PROJECT_CHARTER.md` |
| 当前架构 | `docs/ARCHITECTURE.md` |
| Subject VM 机制合同 | `docs/PARTITIONED_SUBJECT_GRAPH_VM.md` |
| 当前科学问题 | `docs/SCIENTIFIC_ISSUES.md` |
| Stage 3C 冻结结果 | `docs/results/SUBJECT_VM_STAGE3C_RESULTS.md` |
| Stage 3C-40 决策 | `protocols/decisions/subject_graph_vm_stage3c40_categorical_boundary_v1.json` |
| 当前迭代记录 | `docs/迭代/v0.159_D1-Z_主体图Stage3C40_精确categorical边界机会审计.md` |
