# 当前科学问题

## 1. 职责

本文档只记录当前尚未解决的科学问题。冻结证据由 `docs/results/` 汇总；工程缺陷和发布问题不得写入此处。

状态值为 `OPEN`、`BLOCKED` 和 `PARKED`。

## 2. 活动问题注册表

| ID | 类型 | 状态 | 问题 | 当前证据边界 |
|---|---|---|---|---|
| SG-03 | 证据语义 | OPEN | 不引入固定价值函数时，逐组件 Objective-Fact 能否支持任何 retention 决策？ | 在建立非标量决策合同前，不授权 retention study。 |
| SG-04 | Bootstrap 通用性 | PARKED | 哪些结果依赖 normalized-dot/latest/top-1 bootstrap addressing？ | crossing 结果获得独立复现后再比较。 |
| SG-05 | 持续性 | BLOCKED | 临时 graph-parameter 效应能否在独立论证的决策规则下持续？ | 需要可复现下游证据和单独的 keep/revert 合同。 |
| SG-06 | Topology evolution | BLOCKED | topology、readout 和 addressing 能否演化而不退化为不可诊断搜索？ | 需要成本、mutation/development 时程、inheritance、neutralization 和健康 source 资格。 |
| SG-07 | 决策边界可观测性 | OPEN | 连续内部差异距离 categorical sampled-action 边界的精确数值距离是多少？ | 语义中立 categorical sampling trace 已完成并通过 action、RNG、checkpoint 与 branch identity 完整性门；下一步为 Stage 3C-40 只读精确边界审计。 |
| ENV-01 | 环境 | PARKED | 环境能否为分化能力持续提供正交机会？ | 只能作为 `[EVOLVE-ENV]` 恢复，并包含守恒与 source-health gate。 |
| ENV-02 | 人口结构 | OPEN | source checkpoint 是否足以支持演化解释，而不仅是短程机制诊断？ | 需要 population、descendant、generation depth、founder replacement 与 checkpoint stability gate。 |
| SOC-01 | 身份 | BLOCKED | 实体死亡后，延迟 partner evidence 如何继续存在而不附着到回收行？ | 需要历史 subject identity，以及 retention、inheritance、eviction 与 regional-branch 语义。 |

## 3. SG-07：精确 action boundary 可观测性

Stage 3C-39 表明两个 panel 的 continuous divergence 频率、幅度、晚期 tick 分布和已导出的 selected-action probability 变化大量重叠，独立 panel 并不整体更弱。现有摘要也不存在能隔离 crossing source 的单调幅度阈值。

但冻结 trace 只保存已选 action 的概率，没有完整 masked policy logits，也没有精确 counter-based categorical draw；因此不能重建其他 action 的竞争关系或计算随机采样边界距离。这些字段已由 `[ENGINEERING]` trace 导出并通过语义中立性审计。Stage 3C-40 只能读取冻结 trace，不能修改 sampling、exposure、source panel 或 crossing 定义。

## 4. SG-03：Objective-Fact 不是价值

post-commit Objective-Fact 没有内置正负含义。分析不得使用未声明权重求和，不得挑选看起来有利的坐标，不得从资源丰度推导 reward，也不得根据方向混合的组件授权 keep/revert。

## 5. 暂停的环境与 topology 问题

环境变化必须标记为 `[EVOLVE-ENV]`；topology、genetics、developmental expression 与 inherited graph capability 变化必须标记为 `[EVOLVE-SUBJECT]`。二者都不得作为未标记实验插入当前 fixed-bootstrap 主线。

## 6. 不属于本文档的内容

GPU 可用性、测试发现、source fingerprint、console-entry metadata、打包、patch replay、archive pruning、文件权限和 Git 命令格式都属于工程或交付问题，不是科学问题。

## 7. 更新规则

暂定观察保留在分析产物或当前迭代记录中。验证后的结果只进入 `docs/results/` 一次。只有当未解决问题被新增、实质收窄、阻塞或暂停时，才更新本注册表。
