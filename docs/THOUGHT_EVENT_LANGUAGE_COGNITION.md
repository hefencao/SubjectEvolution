# ThoughtEvent、思维链与语言认知研究合同

状态：**设计约束与研究议程；尚未实现**
适用边界：统一 Subject Graph 后续 `[EVOLVE-SUBJECT]` 能力、通信/语言实验与观察者侧跨世界分析。

本文档将思维链、较长期记忆、主体间信号与语言研究放在同一设计边界内。它不声明当前 runtime 已经具有前向 ThoughtEvent recall、语言、对象词、组合语法或跨世界认知同态，也不授权通过固定 reward、confidence、词典或人工语义标签塑形主体。

## 1. 总体立场

项目采用以下统一关系：

```text
分布式 node_state
    负责当前连续计算

统一 ThoughtEvent arena
    保存可重新寻址的内部思考事件

Subject Graph
    决定旧 ThoughtEvent 与新 observation 如何共同参与后续处理

communication interface
    将内部图状态投影为可传播 SignalEvent，并将接收信号路由回统一图
```

思维链不是单独动作，也不是固定长度的显式文本链。语言不是与认知平行的独立网络，也不是外部词典。两者都必须建立在统一 Subject Graph、稳定 subject identity、物理信息通道和可审计成本上。

## 2. 思维链与较长期记忆的统一表示

### 2.1 一种 ThoughtEvent，而不是两种 token

极短暂思维链与较长期记忆必须使用同一种 ThoughtEvent vector、event identity 和 lineage 合同。不得建立：

```text
short_thought_token
→ 固定转译器
→ memory_thought_token
```

允许的差异只包括：

- age 与 remaining retention；
- 最近访问时间与可达索引；
- arena 容量竞争；
- 写入、保留和读取成本；
- 工程上的近期索引与稀疏远期索引。

工程缓存层级不能升级为认知类型边界。近期 token 与较旧 token 必须保持相同 comparator、readout format 和 graph ingress。

### 2.2 `node_state` 与 ThoughtEvent 的职责

`node_state` 负责：

- 当前连续 activation state；
- 局部 retention、routing 和 gate 状态；
- 高频且可能每 tick 更新的内部计算；
- 不需要逐次物化为事件的中间量。

ThoughtEvent 负责：

- graph-defined 时刻产生的有界内部表示；
- 跨 tick 重新寻址；
- 保存多个不同加工深度的思考片段；
- parent DAG 与 source/branch/checkpoint lineage；
- 与后续 Objective-Fact 保持表示层隔离。

不得把完整 node matrix 每 tick 复制进 ThoughtEvent，也不得因为当前 `node_state` 较薄而直接把 action logits 当作内部思考缓存。

### 2.3 ThoughtEvent 核心与结果附件

ThoughtEvent 的不可变核心至少应能够表达：

- token vector；
- origin tick、subject 与 activation/event identity；
- parent ThoughtEvent identities；
- parent contribution 或 read identity；
- graph/configuration/branch/checkpoint lineage。

世界结算后可以追加独立附件：

- sampled/realized action；
- Objective-Fact；
- association、modulation 或 transaction identity。

这些附件不得无条件拼入 thought vector。Objective-Fact 不具有固定正负价值，ThoughtEvent 也不得被系统标记为“正确”“错误”“有毒”或“无效”。

### 2.4 思考链是 DAG，不预设“第几轮”

一个新 ThoughtEvent 可以同时依赖：

- 当前 observation；
- 上一 tick 的连续 node state；
- 一个或多个旧 ThoughtEvent。

因此 lineage 通常是有向无环图，而不是简单链或固定 ring buffer。研究者可以从 lineage 审计加工深度，但主体图不应获得人工注入的“这是第 N 轮思考”语义。

首版必须明确：

- parent 数量上限；
- 是否允许同一 parent 重复出现；
- 是否只读取前一 tick 以前已提交的 ThoughtEvent；
- 如何禁止同 tick 自引用和 lineage cycle；
- lineage metadata 的存储与计算成本。

### 2.5 不增加独立 `RETHINK` 或 confidence halt gate

当前计划不增加独立 `RETHINK` action。思考与外部行动可以跨 tick 并行延续，不需要模仿 LLM 的 final-answer halt condition。

不得通过：

```text
confidence < threshold
→ 抑制所有外部动作
```

重新引入 `NO_ACTION`。如果未来需要低代价/低扰动行为，应建立独立生态行为合同，明确物理效果、机会成本和 action competition。

只有未来引入同一世界 tick 内多轮内部子步时，才需要独立研究 internal scheduler 的停止条件与计算预算。

## 3. 前向 recall 的最小边界

### 3.1 Read head 只是候选实现，不是已验证认知模块

可研究少量内容寻址 read heads，但不得预设固定 `Exploit`、`Explore`、`Contrast` 角色。多个 read head 如果存在，应共享通用原语，并允许其参数、路由和使用方式在独立合同中演化或比较。

首版不应让每个 graph node 对全部历史 ThoughtEvent 进行稠密 temporal attention；这会形成全局记忆总线，旁路 graph topology，并使成本随节点数和历史容量相乘。

### 3.2 两阶段时序

为避免“本轮节点激活决定 recall、recall 又反向决定同一激活”的循环依赖，首个候选实现应保持确定性阶段：

```text
阶段 A：当前 observation + 先前 retained state
→ query/read request

有界 ThoughtEvent candidate selection
→ 少量 recalled vectors

阶段 B：recalled vectors 经获准 ingress 进入统一图
→ 完整 activation
→ 新 ThoughtEvent 与 action potentials
```

第一版不允许读取本 tick 尚未提交的新 ThoughtEvent。

### 3.3 防止 echo chamber

仅做相似度 top-k 可能造成重复召回与 lineage 垄断。第一版必须观测：

- 连续 tick 候选重叠率；
- recalled token age 分布；
- parent 与 child 的内容相似度；
- 单一 lineage 的 arena 占比和后代数量；
- 新 observation contribution 与 recall contribution；
- recall 前后 token diversity；
- 同一 token 或近重复 token 的重复读取。

lineage cap、near-duplicate suppression、多 head、temperature、stochastic retrieval 或 novelty-sensitive route 只能在观察到相应问题后作为独立分支实验，不能预装为最终认知角色。

### 3.4 成本与容量

下列活动必须分别支付可审计成本：

- node activation；
- edge transmission 与 bandwidth；
- retained node state；
- ThoughtEvent emission；
- arena retention；
- candidate search；
- top-k/read-head 读取；
- recalled vector 的 graph ingress。

带宽和成本可以形成信息选择压力，但不能提前宣称必然产生抽象。若图读取多个旧 thought 后生成 summary ThoughtEvent，该 summary 必须是 Subject Graph 的正常输出，而不是存储系统强制压缩。

## 4. 分阶段实现与资格

### T1：统一 ThoughtEvent 基础设施

只实现 schema、identity、parent DAG、bounded arena、lifecycle metadata、checkpoint/clone/branch identity、成本计量和默认关闭。不接入前向 recall。

### T2：只读退化审计

审计当前 token 的频率、重复度、信息漂移、lineage 结构、容量和跨 source 差异。若 token 本身退化，不得直接接入 recall。

### T3：最小短期前向 recall

使用单 read path 或少量无固定角色 read heads，只读取已提交 ThoughtEvent；与无 recall、token 内容打乱、lineage 打乱和等成本 control 比较。

资格环境应包含短延迟的信息依赖，但不得用固定 scalar reward 取代生态后果。

### T4：回声治理与多头资格

只有观察到实际同质化、候选塌缩或 lineage 垄断后，才分别测试 diversity suppression、多 head、age-sensitive candidate generation 或随机化读取。

### T5：连续 retention

第一阶段只记录 reactivation、reference count、age 与后代数量，不立即让它们决定寿命。高调用频率既可能表示复用，也可能表示自激回声，不能自动解释为“有用”。

## 5. 通信、信号与语言

### 5.1 统一图上的 communication interface

未来“语言区域”只能被定义为 communication interface region：

- 将内部图状态投影为可发送 signal；
- 对 signal 进行时序化和物理传播；
- 记录来源、强度、延迟、噪声与成本；
- 将接收到的 SignalEvent 路由回统一 Subject Graph。

它不拥有：

- 对象概念；
- 方位概念；
- 危险或高价值语义；
- 固定词义；
- 预设语法角色。

区域只是塑形和接口偏置，不是独立语言认知网络。语言单位可以成为分布式认知状态的公共可传输把手，但不等于完整认知状态。

### 5.2 ThoughtEvent 与 SignalEvent 必须分离身份

内部 ThoughtEvent 与外部 SignalEvent 是不同事件：

```text
ThoughtEvent / node state
→ signal emission mapping
→ SignalEvent 经世界传播
→ receiver sensory ingress
→ receiver graph activation
→ 新 ThoughtEvent
```

二者可以共享可学习/可演化投影，但不得共享事件 identity。SignalEvent 必须具有发送者、传播路径、接收范围、时序、噪声和物理成本。

### 5.3 语言资格层级

必须区分：

1. **共享信号约定**：任意 signal 在多个主体间稳定改变行为；
2. **跨情境对象指称**：signal 的稳定成分跟随对象身份，而不是固定路径、地点、结果或发送者；
3. **组合结构**：对象、关系和状态成分可以在未见组合中重组；
4. **认知复用**：接收 signal 后形成可保留、可继续加工的内部状态，而不是直接触发固定动作。

达到较低层级不能自动宣称达到更高层级。

## 6. 催生语言的环境约束

### 6.1 非对称可观测性

危险区或高价值区可以对接收者不可直接观察，但必须存在自然获得该信息的主体、历史或感知路径。若只有外部系统知道答案，则产生的是 oracle 指令，不是原生主体间语言。

### 6.2 跨情境解纠缠

若“花盆”始终位于通往高价值区的同一条路径，signal 可能只表示：

- 沿路前进；
- 安全方向；
- 高价值；
- 跟随发送者；
- 固定动作序列。

要资格化对象指称，花盆必须跨位置、方向、危险状态、价值状态和发送者出现；高价值、危险和方向也必须独立变化。

### 6.3 因子化与未见组合

可构造对象、关系与状态的因子化环境，例如：

```text
对象：花盆 / 石头 / 树 / 门
关系：北侧 / 南侧 / 内部 / 后方
状态：危险 / 安全 / 高价值 / 空
```

通信带宽应不足以给所有完整组合分配独立整体码。组合资格必须在保留的未见组合上测试，不能仅根据训练场景内成功推断语法。

### 6.4 强反馈的边界

强生态后果可以加速筛选共享 code，但不能定义词义。极端单一反馈容易选择固定路线、无条件服从或 sender identity shortcut。语言优势应来自跨场景复用，而不是单一环境漏斗。

## 7. 通过原生语言反向干预世界

观察者可以在原生通信形成后尝试发布消息，但必须使用同一物理 SignalEvent channel：

- 相同带宽；
- 相同序列约束；
- 相同传播延迟、噪声和衰减；
- 相同感知入口；
- 可识别但不具有天然绝对可信度的来源。

不得直接向主体图写入推断出的概念向量。世界频道也不能无成本、无延迟、全局可靠，否则主体可能只学习“该来源永远正确”。

外部解释必须通过反事实测试：新位置、对象/状态拆分、token 替换、顺序打乱、冲突消息和来源替换。只有在这些条件下仍保持组合效果，才有资格声称观察者识别了原生语言结构。

## 8. 跨 seed/区域的对象指称差异

### 8.1 不按词形、node ID 或 region 硬对齐

不同 seed、地理区域、谱系或群体可能对同一对象形成：

- 不同 SignalEvent 形式；
- 不同 token 坐标方向；
- 不同 node/edge topology；
- 不同区域分布；
- 不同对象—关系分解方式。

因此相同对象指称不要求相同词形、相同 node identity 或相同 region。region 是发育偏置，不是语义所有者。

### 8.2 四个比较层级

跨世界比较至少区分：

1. **形式等价**：信号形式恰好相同；通常不应期待；
2. **指称分区等价**：不同 signal 对世界对象/状态作出相似区分；
3. **关系结构等价**：对象、关系、状态和组合之间的变换结构相似；
4. **干预功能等价**：对候选内部结构或 signal mapping 的干预产生相似的行为与 ThoughtEvent 后果。

不能从第 1 层失败推断语言或认知不等价，也不能仅凭第 2 层就宣称图结构同构。

### 8.3 对齐方法的约束

观察者侧对齐应使用标准化 probe 和反事实：

- 同一对象在多情境下的 signal/ThoughtEvent 响应；
- 对象存在、位置、关系和状态的独立操纵；
- sender/receiver identity 交换；
- 候选 subgraph/region 的有界消融；
- 在部分对象/关系上估计映射，在未见组合上验证；
- 保留符号置换、node permutation 和冗余 topology 的等价可能。

任何 observer-side decoder 或映射都不得反馈进 runtime cognition，也不能把分析坐标当成主体自己的语义轴。

## 9. 基础认知/语言的结构收敛假设

### 9.1 成本约束编码同态假设

在相似环境统计、带宽和代谢成本下，不同 seed/区域可能形成不同表面编码，却在以下方面收敛：

- 常见或高复用区分具有更低表达/读取成本；
- 稀有组合通过较长或组合式路径表达；
- 对象、关系和状态的组合结构可由一个世界映射到另一个世界；
- 相对 code cost、路径深度或 signal length 的排序相似。

这可以暂称为**成本约束编码同态假设**。它与哈夫曼编码的相似性仅在于：有限带宽下，环境出现频率和使用需求可能推动不同长度/成本的编码。

### 9.2 不是字面上的哈夫曼编码

不得预设主体编码必然：

- 离散；
- 无损；
- prefix-free；
- 静态；
- 由单一符号树表示；
- 达到信息论最优；
- 只由对象出现频率决定。

主体编码还受行动、空间、来源、噪声、身体成本、时间延迟、群体互动和图拓扑约束。更准确的研究对象是：

> 不同世界的认知/语言结构之间，是否存在保持指称关系、组合运算和相对成本序的映射。

### 9.3 同态、同构与功能收敛必须分开

- **表面同构**：token、树或图几乎一一对应；预期很弱；
- **结构同态**：多个 seed-specific 状态可以映射到共同功能结构，并保留部分组合关系；
- **功能收敛**：即使内部拓扑不同，也能在标准化反事实中完成相似的信息区分和通信；
- **成本序收敛**：常见/高复用区分在各世界中相对更便宜，但具体 code 不同。

项目优先检验后面三层，不以图节点逐一匹配作为前置要求。

### 9.4 资格证据

该假设至少需要：

- 多个独立 seed、区域或文化谱系；
- 相同或明确可比较的环境统计与成本合同；
- 未见组合上的跨世界映射验证；
- code length、能量、延迟和 graph-path cost 的分离报告；
- 与符号置换、随机 code、固定路线和 sender shortcut 的对照；
- 不在同一 panel 上发现映射并宣称独立验证。

可能结果包括完全不收敛、只功能收敛、成本序收敛但结构不同、局部同态或环境依赖方言；任何一种都不能被提前排除。

## 10. 当前禁止项

在单独实现与实验合同建立前，不得：

- 增加 `RETHINK`、`NO_ACTION` 或 confidence gate；
- 建立短期/长期两套 thought 表示；
- 把 Objective-Fact 直接写入 thought vector；
- 给 thought 赋正确/错误/毒性标签；
- 固定 `Exploit/Explore/Contrast` read-head 角色；
- 以 reference count 自动延长 retention；
- 把通信区域定义为具体词义或语言认知所有者；
- 通过内部 API 注入“土著语言”概念；
- 把路标触发码称为对象词；
- 把成本瓶颈导致压缩当作已证实抽象；
- 把跨 seed observer mapping 反馈回主体或用于选择性演化。

## 11. 下一实现边界

下一 `[EVOLVE-SUBJECT]` 首轮只建立 T1 统一 ThoughtEvent 基础设施，不接语言、不接外部世界频道，也不直接启用前向 recall。实现必须保持当前 Stage 3C bootstrap 可重现，并为后续 T2 退化审计提供足够 identity、lineage、容量和成本证据。

语言与跨世界编码同态继续作为后续研究议程；它们依赖 ThoughtEvent、通信接口、非对称可观测环境和跨 seed 观察工具，不应与 T1 一次性实现。
