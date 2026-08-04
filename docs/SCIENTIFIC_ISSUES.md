# 当前科学问题

## 1. 职责

本文档只记录当前尚未解决的科学问题。冻结证据由 `docs/results/` 汇总；工程缺陷和发布问题不得写入此处。

## 2. 活动问题注册表

| ID | 类型 | 状态 | 问题 | 当前证据边界 |
|---|---|---|---|---|
| SG-03 | 证据语义 | OPEN | 不引入固定价值函数时，逐组件 Objective-Fact 能否支持 retention 决策？ | 在建立非标量决策合同前不授权 retention study。 |
| SG-04 | Bootstrap 通用性 | PARKED | 哪些结果依赖 normalized-dot/latest/top-1 bootstrap addressing？ | 当前 crossing 因果链完成 source-pressure 分解后再比较。 |
| SG-05 | 持续性 | BLOCKED | 临时 graph-parameter 效应能否在独立论证的决策规则下持续？ | 需要可复现下游证据和单独 keep/revert 合同。 |
| SG-06 | Topology evolution | BLOCKED | topology、readout 和 addressing 能否演化而不退化为不可诊断搜索？ | 需要成本、development、inheritance、neutralization 和健康 source 资格。 |
| SG-09 | 边界压力来源 | OPEN | 为什么原 panel 的部分 source 产生足以耗尽 draw margin 的 CDF 边界压力，而独立 panel 全部保留正余量？ | Stage 3C-41 只读分解各 action 的 masked-logit、概率和 CDF endpoint 贡献；不得增加 panel 或拟合后见阈值。 |
| ENV-01 | 环境 | PARKED | 环境能否为分化能力持续提供正交机会？ | 只能作为 `[EVOLVE-ENV]` 恢复，并包含守恒与 source-health gate。 |
| ENV-02 | 人口结构 | OPEN | source checkpoint 是否足以支持演化解释，而不仅是短程机制诊断？ | 需要 population、descendant、generation depth、founder replacement 与 checkpoint stability gate。 |
| SOC-01 | 身份 | BLOCKED | 实体死亡后，延迟 partner evidence 如何继续存在而不附着到回收行？ | 需要历史 subject identity 以及 retention、inheritance、eviction 语义。 |

## 3. SG-09：边界压力来源

Stage 3C-40 已获得每个连续 divergence 事件的完整 action mask、masked logits、概率、CDF、uniform draw 与 sampled interval。实际 crossing 可精确表示为：朝 draw 方向移动的 interval 边界压力不小于原 interval 余量。

原 panel 有四个 alignment-specific crossing 事件；独立 panel 的最大压力/余量比为 `0.68848`，全部小于 1。draw proximity 或 CDF shift 的绝对大小单独都不能解释 crossing，alignment 模式和边界移动方向同样重要。

下一步必须在已有 trace 上逐 action 分解：哪些 logit 改变移动了 selected interval 的下界或上界，哪些竞争 action 吸收或释放概率质量，以及这种模式与 source state、action 类型和 alignment mode 的关系。不能把这些量事后组合成 reward 或经验分类分数。

## 4. Objective-Fact 不是价值

post-commit Objective-Fact 没有内置正负含义。分析不得使用未声明权重求和，不得挑选看起来有利的坐标，也不得根据方向混合的组件授权 keep/revert。

## 5. 不属于本文档的内容

GPU 可用性、测试发现、source fingerprint、console-entry metadata、打包、patch replay、archive pruning、文件权限和 Git 命令格式属于工程或交付问题。

## 6. 更新规则

暂定观察保留在分析产物或当前迭代记录中。验证后的结果只进入 `docs/results/` 一次；只有未解决问题被新增、实质收窄、阻塞或暂停时才更新本注册表。
