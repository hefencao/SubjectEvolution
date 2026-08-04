# 当前科学问题

## 1. 职责

本文档只记录当前尚未解决的科学问题。冻结证据由 `docs/results/` 汇总；工程缺陷和发布问题不得写入此处。

## 2. 活动问题注册表

| ID | 类型 | 状态 | 问题 | 当前证据边界 |
|---|---|---|---|---|
| SG-03 | 证据语义 | OPEN | 不引入固定价值函数时，逐组件 Objective-Fact 能否支持 retention 决策？ | 在建立非标量决策合同前不授权 retention study。 |
| SG-04 | Bootstrap 通用性 | PARKED | 哪些结果依赖 normalized-dot/latest/top-1 bootstrap addressing？ | 当前 crossing 因果链完成 activation-source 分解后再比较。 |
| SG-05 | 持续性 | BLOCKED | 临时 graph-parameter 效应能否在独立论证的决策规则下持续？ | 需要可复现下游证据和单独 keep/revert 合同。 |
| SG-06 | Topology evolution | BLOCKED | topology、readout 和 addressing 能否演化而不退化为不可诊断搜索？ | 需要成本、development、inheritance、neutralization 和健康 source 资格。 |
| SG-09 | REST output 来源 | OPEN | 不同 source history 为什么产生不同符号和幅度的 `REST` action-port output，并进一步形成不同的 CDF endpoint pressure？ | Stage 3C-41 已确认 policy-level 非零 logit source 全部为 `REST`；下一步先完成语义中立 activation contribution trace，之后才能审计 graph 内部来源。 |
| ENV-01 | 环境 | PARKED | 环境能否为分化能力持续提供正交机会？ | 只能作为 `[EVOLVE-ENV]` 恢复，并包含守恒与 source-health gate。 |
| ENV-02 | 人口结构 | OPEN | source checkpoint 是否足以支持演化解释，而不仅是短程机制诊断？ | 需要 population、descendant、generation depth、founder replacement 与 checkpoint stability gate。 |
| SOC-01 | 身份 | BLOCKED | 实体死亡后，延迟 partner evidence 如何继续存在而不附着到回收行？ | 需要历史 subject identity 以及 retention、inheritance、eviction 语义。 |

## 3. SG-09：REST output 来源

Stage 3C-41 对 Stage 3C-40 已冻结的 90 个 top boundary opportunity 做了逐 action 分解。180 个 mode-event comparison 中，130 个具有非零 masked-logit 变化，且全部只改变 `REST` logit。其他 action 的 probability delta 是 softmax 耦合后的质量重分配，不是独立 action-logit source。

六个 crossing 同时包含正、负 `REST` logit delta；五个 crossing 的 REST probability driver 被其他 action 的概率变化部分抵消。独立 panel 中存在比 crossing 更大的 `|REST logit delta|` 和 `|REST probability delta|`，但由于 selected action 顺序、endpoint 方向、抵消和原 draw margin 不同，仍未 crossing。

所以 policy-level pressure source 已收窄到 `REST` output，但 source history→temporary write→node/edge activation→REST output 的内部路径尚不可观测。不得把 `REST` 解释为价值、静息偏好或 reward。

## 4. Objective-Fact 不是价值

post-commit Objective-Fact 没有内置正负含义。分析不得使用未声明权重求和，不得挑选看起来有利的坐标，也不得根据方向混合的组件授权 keep/revert。

## 5. 不属于本文档的内容

GPU 可用性、测试发现、source fingerprint、console-entry metadata、打包、patch replay、archive pruning、文件权限和 Git 命令格式属于工程或交付问题。

## 6. 更新规则

暂定观察保留在分析产物或当前迭代记录中。验证后的结果只进入 `docs/results/` 一次；只有未解决问题被新增、实质收窄、阻塞或暂停时才更新本注册表。
