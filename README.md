# SubjectEvolution v0.160.0

SubjectEvolution 是一个实验性模拟项目，用于在不预设奖励和人类社会语义的前提下，研究类似主体的内部组织如何出现、变化并产生因果影响。

v0.160.0 完成 Stage 3C-41 action-logit 与 CDF boundary pressure 来源分解。研究确认 Stage 3C-40 top opportunity 中所有非零 masked-logit 变化都只发生在 `REST` action port；其他 action 的概率变化来自 softmax 耦合，且 `REST` logit 的符号或幅度不能单独区分 crossing。

## 文档索引

- 项目宪章：[`docs/PROJECT_CHARTER.md`](docs/PROJECT_CHARTER.md)
- 项目治理：[`docs/PROJECT_GOVERNANCE.md`](docs/PROJECT_GOVERNANCE.md)
- 当前架构：[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- 类型化任务树：[`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)
- 当前科学问题：[`docs/SCIENTIFIC_ISSUES.md`](docs/SCIENTIFIC_ISSUES.md)
- Stage 3C 冻结结果：[`docs/results/SUBJECT_VM_STAGE3C_RESULTS.md`](docs/results/SUBJECT_VM_STAGE3C_RESULTS.md)
- Subject Graph VM 合同：[`docs/PARTITIONED_SUBJECT_GRAPH_VM.md`](docs/PARTITIONED_SUBJECT_GRAPH_VM.md)
- 仓库代理规则：[`AGENTS.md`](AGENTS.md)

## 当前科学前沿

Stage 3C-41 已冻结。下一项为 `[ENGINEERING]` 语义中立 Subject VM activation contribution trace；完成该工程门前，Stage 3C-42 source-history→activation→REST output 分解保持阻塞。
