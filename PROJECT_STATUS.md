# Subject Evolution 项目状态（v0.6.0）

## 本轮完成：K2 局部后果记录与经验更新

本版本在 K1 的动态知识副本和有代价交换基础上实现：

- `dynamic-knowledge-k2-v1`；
- `local-context-v1`；
- `local-outcome-v1`；
- 不可变 `KnowledgeOutcomePlan`；
- 五维局部行动后果：energy、integrity、material、information、reproduction opportunity；
- 成功、失败和部分成功状态；
- 副本本地 Welford mean/M2/sample count；
- 私有经验内容创建；
- 有代价本地验证和置信度更新/衰减；
- 外来知识必须在后续 tick 亲历匹配后果才能提高本地置信度；
- 发送副本最新本地统计的复制和损坏变体；
- outcome/update 日志、metrics、checkpoint 和 manifest/scientific-validity 元数据；
- K1 schema 与 K2 learning-off 向后兼容。

遗传策略仍为 `inherited-linear-policy-v1`。K2 知识不会进入策略 features、logits、控制提案、
intent 或 action resolver。

## 短周期验证

本轮遵照短迭代策略，没有默认运行 500 ticks。验证使用 CPU、seed 10001、1000 初始实体、
50 ticks，并在 tick 25/50 保存检查点：

- K1-compatible / learning off；
- K2 private learning；
- K2 costed exchange + learning。

每个条件独立复跑两次。所有非计时 metrics、知识日志、演化诊断、run metadata 非计时字段，
以及两个检查点中的全部 32 个数组均完全一致。

旧 v0.5.0 K1 与 v0.6.0 在 learning off 条件下的 104 个共同非计时指标、29 个共同检查点数组、
知识事件和传输日志完全一致。v0.6.0 仅增加三个副本本地统计数组。

这些短运行只验证实现边界、确定性和兼容性，不构成长期适应优势、选择效应或主体性结论。

## 当前阶段状态

| 功能 | 状态 |
|---|---|
| 动态知识副本 | K1 已完成 |
| 有代价知识交换 | K1 已完成 |
| 局部后果记录与经验更新 | K2 已完成 |
| 知识残差进入策略 | 未实现，K3 |
| 知识复制谱系进入主体图 | 未实现，K4 |
| 完整设备驻留世界循环 | 未实现 |
| 完整主体图数据库及任意嵌套主体 | 未实现 |
| checkpoint 全世界恢复与离线反事实重放 | 未实现 |
| 信息模板寄生主体 | 未实现 |
| 完整主体性评分 | 未实现 |
| Hero 强化学习 | 未实现 |
| 任意信息通道 schema | 未实现 |

## 下一阶段建议：K3

K3 应使用新的、显式版本化的策略 schema，将本地知识副本形成的稀疏残差加入遗传先验
logits，并分别记录遗传贡献、知识贡献和最终行动贡献。K3 开始前应先增加：

1. no-knowledge、private、costed-exchange 和 zero-cost 对照；
2. 知识贡献为零时与 K2 的逐 tick 完全等价测试；
3. action mask、intent/plan/commit 和随机流不被知识路径绕过的测试；
4. 遗传策略坍缩与知识分化的独立指标；
5. 多 seed 短实验后再决定是否进行长周期运行。
