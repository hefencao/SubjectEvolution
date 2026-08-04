# SubjectEvolution 当前项目状态

版本：**0.161.0**

## 当前迭代身份

- 进度类型：**`[ENGINEERING]` 运行时观测设施**
- Git 标题：**`[ENGINEERING] subject-vm: export neutral activation contribution trace`**
- Git 分支：**`engineering/subject-vm-activation-contribution-trace`**
- 工作流档位：**`STANDARD-CODE` + `RELEASE-HANDOFF`**
- 当前冻结科学前沿：**Stage 3C-41**
- 下一项科学边界：**Stage 3C-42 只读 activation contribution 来源审计**

## 类型化任务进度树

```text
SubjectEvolution
├── [MAIN-EXP] 主线实验
│   └── D1-Z 统一 Subject Graph VM
│       ├── [FROZEN] Stage 3C-40 精确 categorical action-boundary opportunity
│       ├── [FROZEN] Stage 3C-41 action-logit/CDF pressure source 分解
│       ├── [NEXT] Stage 3C-42 source-history→activation→REST output 来源审计
│       └── [BLOCKED] retention、learned weight 与 topology evolution
├── [BRANCH-EXP] 分支实验
│   └── [PARKED] 低代价/低扰动 action 的独立行为合同；不得与当前 action 集合混入
├── [PARAM-EXP] 代码参数探索
│   └── 当前无活动项
├── [EVOLVE-ENV] 环境/底物演化代码
│   └── [PARKED] 持续多压力环境与 source-health 工作
├── [EVOLVE-SUBJECT] 主体能力演化代码
│   └── [BLOCKED] topology/readout/addressing evolution 尚无完整合同
├── [ENGINEERING] 运行时、工具、测试与打包
│   ├── [DONE] 语义中立 categorical sampling trace
│   ├── [DONE] 语义中立 Subject VM activation contribution trace
│   └── [PARKED] 自动判断本地处理与 artifact handoff 意图
└── [DOC-GOV] 文档治理
    └── [DONE] 活动规范文档为中文权威文本
```

## 本轮工程冻结判断

activation contribution trace 直接消费同一次权威 graph activation 已计算出的 node、edge、output-port 与 temporary-write lineage，不重新执行图、不读取随机流，也不向 runtime 回馈。

正式 fresh continuation 与 paired-branch 对照确认：

- sampled action 与 selected probability 完全一致；
- categorical action/RNG JSONL 逐字节一致；
- checkpoint authoritative state hash 完全一致；
- paired branch identity 文件逐字节一致；
- node accumulator、edge bounded transmission、output-port 聚合与 clipped action potential 可从 trace 精确重建；
- guarded-live 与 read-only-control temporary-write lineage 符合实际 pre/post/current 状态。

该结果只证明观测设施语义中立，不构成新的科学 Stage，也不证明 trace contribution 具有因果、价值或信用语义。

## 暂停的 action 方案

`NO_ACTION` 不进入当前设计。它会引入不自然且容易混淆的“未形成动作”语义。

低代价/低扰动 action 可能比 `NO_ACTION` 更符合现有行为系统，但它会改变生态成本、action competition 与 sampling boundary，必须在独立 `[BRANCH-EXP]` 或 `[EVOLVE-SUBJECT]` 合同中处理。当前仅记录为 `PARKED`，不得在 Stage 3C-42 前混入主线。

## 下一边界约束

Stage 3C-42 可以只读使用本轮冻结 trace，比较 crossing-positive、alignment-common 与独立 panel 高机会事件中的 node、edge、output gate 和 temporary-write contribution。

不得：

- 修改 Subject VM activation、action sampling、source panel 或 exposure；
- 把执行 contribution 直接解释为因果 attribution；
- 将 `REST` 或任一 node/edge 赋予价值语义；
- 增加 `NO_ACTION` 或低扰动 action；
- 授权 automatic keep/revert、learned weight 或 permanent retention。

## 文档与证据索引

| 需求 | 权威位置 |
|---|---|
| 项目使命与解释边界 | `docs/PROJECT_CHARTER.md` |
| 当前架构 | `docs/ARCHITECTURE.md` |
| Subject VM 机制合同 | `docs/PARTITIONED_SUBJECT_GRAPH_VM.md` |
| 当前科学问题 | `docs/SCIENTIFIC_ISSUES.md` |
| Stage 3C 冻结结果 | `docs/results/SUBJECT_VM_STAGE3C_RESULTS.md` |
| activation trace 工程决策 | `protocols/decisions/subject_vm_activation_contribution_trace_v1.json` |
| 当前迭代记录 | `docs/迭代/v0.161_主体图activation_contribution_trace.md` |
