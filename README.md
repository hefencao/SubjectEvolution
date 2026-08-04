# SubjectEvolution v0.158.0

SubjectEvolution 是一个实验性模拟项目，用于在不预设奖励和人类社会语义的前提下，研究类似主体的内部组织如何出现、变化并产生因果影响。

v0.158.0 增加语义中立的 categorical sampling trace：导出完整 action competition 与 counter-based draw，同时证明 trace 开/关不改变 sampled action、RNG、checkpoint state 或 branch identity。本版本不形成新的科学结论。

## 文档索引

- 项目宪章：[`docs/PROJECT_CHARTER.md`](docs/PROJECT_CHARTER.md)
- 项目治理：[`docs/PROJECT_GOVERNANCE.md`](docs/PROJECT_GOVERNANCE.md)
- 当前架构：[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- 类型化任务树：[`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)
- 当前科学问题：[`docs/SCIENTIFIC_ISSUES.md`](docs/SCIENTIFIC_ISSUES.md)
- Stage 3C 冻结结果：[`docs/results/SUBJECT_VM_STAGE3C_RESULTS.md`](docs/results/SUBJECT_VM_STAGE3C_RESULTS.md)
- Subject Graph VM 合同：[`docs/PARTITIONED_SUBJECT_GRAPH_VM.md`](docs/PARTITIONED_SUBJECT_GRAPH_VM.md)
- 仓库代理规则：[`AGENTS.md`](AGENTS.md)
- 验证与交付档位：[`docs/WORKFLOW_PROFILES.md`](docs/WORKFLOW_PROFILES.md)

## 当前科学前沿

Stage 3C-39 仍是冻结科学前沿。categorical trace 工程边界完成后，下一主线为 Stage 3C-40 只读精确 categorical boundary 审计；不得修改 sampling、exposure、source panel 或 crossing definition。

## 工作区配置

操作员专属的项目外目录保存在被忽略的 `.se-workspace.toml` 中，并由 `se-workspace` 管理。
