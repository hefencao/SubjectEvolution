# SubjectEvolution 当前项目状态

版本：**0.158.0**

## 当前迭代身份

- 进度类型：**`[ENGINEERING]` categorical sampling trace**
- Git 标题：**`[ENGINEERING] policy: export neutral categorical sampling trace`**
- Git 分支：**`engineering/categorical-sampling-trace`**
- 工作流档位：**`STANDARD-CODE` + `RELEASE-HANDOFF`**
- 当前冻结科学前沿：**Stage 3C-39**
- 下一项已授权主线：**Stage 3C-40 精确 categorical boundary 只读审计**

本轮只增加语义中立的观测导出，不形成新的科学 Stage。trace 默认关闭，不属于 configuration identity、checkpoint state 或 branch identity。

## 类型化任务进度树

```text
SubjectEvolution
├── [MAIN-EXP] 主线实验
│   └── D1-Z 统一 Subject Graph VM
│       ├── [FROZEN] Stage 3C-39 action-boundary opportunity transport
│       ├── [NEXT]   Stage 3C-40 精确 categorical boundary 只读审计
│       └── [BLOCKED] retention、learned weight 与 topology evolution
│
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
│   ├── [DONE] trace 开/关 fresh-run 与 paired-branch state/identity 审计
│   └── [PARKED] 自动判断本地处理与 artifact handoff 意图
└── [DOC-GOV] 文档治理
    └── [DONE] 活动规范文档统一为中文权威文本
```

## 工程边界

trace 导出完整 action mask、masked logits、概率向量、CDF、counter-based RNG key、uniform draw、sampled action 及其 CDF 区间。普通采样与 trace 采样共用同一计算核；writer 不生成随机数，不参与 policy 或 world settlement。

完整性审计要求 trace 开/关满足：sampled action、selected probability、checkpoint state hash、checkpoint lineage 与 branch identity 全部一致，并能从导出字段逐事件重建 RNG key、CDF 区间和 sampled action。

## 当前科学判断

Stage 3C-39 的结论未改变：现有摘要无法解释两个 panel 的 sampled-action crossing 差异。新 trace 仅解除可观测性阻塞，使 Stage 3C-40 可以在冻结 protocol 下重建精确 categorical competition；它本身不支持 value、causal-credit quality、keep/revert、learned weight 或 retention。

## 文档与证据索引

| 需求 | 权威位置 |
|---|---|
| 项目使命与解释边界 | `docs/PROJECT_CHARTER.md` |
| 当前架构 | `docs/ARCHITECTURE.md` |
| Subject VM 机制合同 | `docs/PARTITIONED_SUBJECT_GRAPH_VM.md` |
| categorical trace 合同 | `protocols/decisions/categorical_sampling_trace_v1.json` |
| 当前科学问题 | `docs/SCIENTIFIC_ISSUES.md` |
| 当前迭代记录 | `docs/迭代/v0.158_工程_categorical采样trace.md` |
