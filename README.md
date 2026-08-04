# SubjectEvolution v0.164.0

SubjectEvolution 是一个实验性模拟项目，用于在不预设奖励和人类社会语义的前提下，研究类似主体的内部组织如何出现、变化并产生因果影响。

v0.164.0 完成统一 ThoughtEvent T1 基础设施：新增默认关闭的不可变事件核心、parent DAG、bounded arena、生命周期、checkpoint/clone/branch identity 与计数成本。该版本不接入前向 recall、read head、语言或世界频道。

## 文档索引

- 项目宪章：[`docs/PROJECT_CHARTER.md`](docs/PROJECT_CHARTER.md)
- 项目治理：[`docs/PROJECT_GOVERNANCE.md`](docs/PROJECT_GOVERNANCE.md)
- 当前架构：[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- 类型化任务树：[`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)
- 当前科学问题：[`docs/SCIENTIFIC_ISSUES.md`](docs/SCIENTIFIC_ISSUES.md)
- Stage 3C 冻结结果：[`docs/results/SUBJECT_VM_STAGE3C_RESULTS.md`](docs/results/SUBJECT_VM_STAGE3C_RESULTS.md)
- Subject Graph VM 合同：[`docs/PARTITIONED_SUBJECT_GRAPH_VM.md`](docs/PARTITIONED_SUBJECT_GRAPH_VM.md)
- ThoughtEvent、思维链与语言研究合同：[`docs/THOUGHT_EVENT_LANGUAGE_COGNITION.md`](docs/THOUGHT_EVENT_LANGUAGE_COGNITION.md)
- 仓库代理规则：[`AGENTS.md`](AGENTS.md)

## 当前科学前沿

Stage 3C-42 继续保持冻结。T1 统一 ThoughtEvent 基础设施已经完成并默认关闭。下一项为 T2 只读退化审计：先检查现有 graph-produced token 的频率、重复度、漂移、容量和成本，在确认表示未退化前不接入前向 recall。语言研究以统一 Subject Graph 与物理 SignalEvent 通道为边界，跨 seed/区域比较必须对齐功能、指称关系和成本结构，而不是硬对齐词形、node ID 或 region。
