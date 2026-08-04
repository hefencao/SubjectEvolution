# 当前科学问题

## 1. 职责

本文档只记录当前尚未解决的科学问题。冻结证据由 `docs/results/` 汇总；工程缺陷和发布问题不得写入此处。

## 2. 活动问题注册表

| ID | 类型 | 状态 | 问题 | 当前证据边界 |
|---|---|---|---|---|
| SG-03 | 证据语义 | OPEN | 不引入固定价值函数时，逐组件 Objective-Fact 能否支持 retention 决策？ | 在建立非标量决策合同前不授权 retention study。 |
| SG-04 | Bootstrap 通用性 | PARKED | 哪些结果依赖 normalized-dot/latest/top-1 bootstrap addressing？ | 当前 Stage 3C 执行链已冻结；后续比较必须与新的思维链能力分离。 |
| SG-05 | 持续性 | BLOCKED | 临时 graph-parameter 效应能否在独立论证的决策规则下持续？ | 需要可复现下游证据和单独 keep/revert 合同。 |
| SG-06 | Topology evolution | BLOCKED | topology、readout 和 addressing 能否演化而不退化为不可诊断搜索？ | 需要成本、development、inheritance、neutralization 和健康 source 资格。 |
| SG-09 | REST output 上游来源 | OPEN | 哪些 history、association 和 modulation 条件使不同 source 产生不同 edge-forward-gate temporary write？ | Stage 3C-42 已解析 temporary write 之后的执行路径，但未解析 proposal 形成原因；当前不继续机械追加 Stage 3C。 |
| SG-10 | 思维链与记忆连续性 | OPEN | 如何让极短暂、频繁更新的思考与较长期记忆共享表示空间，同时支持递归加工而不形成两套 token 数据鸿沟？ | 下一项 `[EVOLVE-SUBJECT]` 实现必须采用统一 ThoughtEvent identity；短期/长期只能在生命周期、索引和访问成本上连续分化。 |
| LANG-01 | 对象指称资格 | OPEN | 如何区分共享行为触发码、跨情境对象指称、组合语言和可复用认知把手？ | 必须使用非对称可观测性、跨情境解纠缠和未见组合；固定路径或极强反馈不能单独证明词义。 |
| LANG-02 | 跨 seed/区域对齐 | OPEN | 同一类型对象在不同 seed、区域或谱系中是否由不同 signal、subgraph 和 region 指称？ | 不按词形、node ID 或 region 硬对齐；需要功能干预、指称分区、关系结构和未见组合上的 observer-side 映射。 |
| LANG-03 | 成本约束编码同态 | OPEN | 相似环境统计与带宽成本下，不同世界的基础认知/语言是否形成保持组合关系与相对成本序的同态结构？ | “类似哈夫曼编码”只作为假设；不预设离散、prefix-free、无损、静态或信息论最优编码。 |
| LANG-04 | 原生语言干预 | BLOCKED | 观察者能否分析原生信号后，通过同一物理频道发布消息并产生可迁移干预？ | 依赖通信接口、语言资格和反事实验证；不得直接向 Subject Graph 注入概念向量或建立绝对可信世界频道。 |
| ENV-01 | 环境 | PARKED | 环境能否为分化能力持续提供正交机会？ | 只能作为 `[EVOLVE-ENV]` 恢复，并包含守恒与 source-health gate。 |
| ENV-02 | 人口结构 | OPEN | source checkpoint 是否足以支持演化解释，而不仅是短程机制诊断？ | 需要 population、descendant、generation depth、founder replacement 与 checkpoint stability gate。 |
| SOC-01 | 身份 | BLOCKED | 实体死亡后，延迟 partner evidence 如何继续存在而不附着到回收行？ | 需要历史 subject identity 以及 retention、inheritance、eviction 语义。 |

## 3. SG-09：REST output 上游来源

Stage 3C-41 已把 policy-level 非零 logit source 收窄到 `REST`。Stage 3C-42 进一步证明，在预冻结的 40 个 mode-event 中，3-tick 与 6-tick exposure 的 REST output difference-in-differences 全部由当前仍生效的 recurrent `edge-forward-gate` temporary write 贡献；inherited node state、state×gate interaction、input、bias 和 output gate 没有形成 exposure DID。

这说明当前 fixed bootstrap 的执行链是：

```text
active edge-forward-gate write
→ delay-one self-edge
→ node-0
→ REST output
```

但 Stage 3C-42 没有解释：哪些 historical event、association winner、eligibility/modulation 条件和 proposal 路由产生了该 write。gate contribution 的绝对幅度也不能区分 crossing 与 noncrossing。该问题继续保持开放，但暂不作为下一轮主线。

## 4. SG-10：思维链与记忆连续性

当前 `node_state` 只提供很薄的连续递归状态；历史 thought token 主要服务 delayed association，没有进入下一轮前向 activation。下一能力需要让旧思考与新信息共同参与后续处理，但不能将“思维链 token”和“记忆 token”设计为两种表示。

首个实现合同必须保持：

- 统一 ThoughtEvent vector 与 identity；
- 短暂链和较长期记忆共享 comparator、readout 格式与 graph ingress；
- 时间尺度差异由 retention lifecycle、近期/稀疏索引和访问成本表达；
- 不设置独立 `RETHINK` action；
- 不把 action preference 或 Objective-Fact 无条件作为 thought 内容回灌；
- 工程缓存层级不得升级为认知语义层级。

是否使用少量 read heads、分布式递归路径或其他可塑路由，将在实现和消融中比较，不能提前当作已验证认知架构。


## 5. LANG-01～04：语言、指称与跨世界结构

语言研究必须从共享 signal convention、对象指称、组合结构和内部认知复用四层逐级资格化。一个沿“花盆—高价值路径”形成的 signal 可能只表示路线、安全、跟随发送者或固定动作，不能直接命名为“花盆”。对象、关系、状态、位置、发送者和结果必须独立变化，并在未见组合中验证。

不同 seed、区域或文化谱系可能形成不同词形、token 方向、node/edge topology 与 region 分布。跨世界比较优先检验：

1. 是否对世界形成相似的指称分区；
2. 对象、关系和状态的组合变换是否可映射；
3. 候选 subgraph 或 signal mapping 的干预后果是否相似；
4. 常见或高复用区分的相对表达、读取和路径成本是否收敛。

“基础认知编码类似哈夫曼编码”被收敛为成本约束编码同态假设：有限带宽可能使常见区分更便宜、稀有组合更长或更组合化，但不预设 prefix code、无损离散符号树或全局最优。不同世界可以表面编码完全不同，只在功能、组合关系或成本序上存在局部同态。

外部反向干预只能通过与原生主体相同的 SignalEvent channel 完成，并需要来源替换、token 替换、顺序打乱、对象/状态拆分和新位置等反事实。完整设计约束见 `docs/THOUGHT_EVENT_LANGUAGE_COGNITION.md`。

## 6. Objective-Fact 不是价值

post-commit Objective-Fact 没有内置正负含义。分析不得使用未声明权重求和，不得挑选看起来有利的坐标，也不得根据方向混合的组件授权 keep/revert。

## 7. 不属于本文档的内容

GPU 可用性、测试发现、source fingerprint、console-entry metadata、打包、patch replay、archive pruning、文件权限和 Git 命令格式属于工程或交付问题。

## 8. 更新规则

暂定观察保留在分析产物或当前迭代记录中。验证后的结果只进入 `docs/results/` 一次；只有未解决问题被新增、实质收窄、阻塞或暂停时才更新本注册表。
