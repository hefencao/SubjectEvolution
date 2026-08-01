# “通用功能张量算子 + 基因重复与表达门控 + 代谢成本”方案评估

状态：长期架构评估；v0.50 已实现固定四槽、前馈组合与氧合/组织/结构生理基底的受限子集，动态复制与任意拓扑仍未实现
适用项目：嵌套主体存在、生态分化与社会演化模拟

## 1. 结论

该方案的总体方向与项目相容，适合作为“固定世界接口内的可演化功能组合层”，但不能原样作为最终架构。

建议保留：

- 固定最大张量布局；
- 有效容量掩码；
- 模块表达门控；
- 输入混合、局部变换与输出路由；
- 模块复制、删除和重联；
- 显式结构与使用成本；
- 模块同源与消融审计。

必须修正：

- “完全没有预设”的表述；
- “纯张量绝对保证 bitwise exact”的表述；
- 单一容量基因和单一能量脑税；
- 把行为映射等同于完整生物器官；
- 复制后自动提高突变率；
- 当前示例代码中的路由、掩码和初始化问题。

## 2. 项目适配度

### 2.1 与现有架构重叠

当前项目已经拥有：

- 可遗传 variable latent router；
- 量化两层 MLP residual；
- inherited discrete Top-k；
- 工作记忆；
- 动态知识内容；
- 路由计算成本；
- 资源亲和；
- 稳定 ID、checkpoint 和反事实干预。

因此，新的通用模块不应简单成为第二套 action-logit residual 网络。它应主要扩展：

- 具身容量；
- 传感和执行器端口；
- 资源转化、储存、信号和连接能力；
- 模块表达、发育、损伤和维护；
- 模块复制与同源谱系。

### 2.2 能实现的新颖性层级

方案能支持的是：

- 同一功能的参数分化；
- 固定输入/输出接口内的组合新功能；
- 若接口连接真实物理模块，可支持具身功能分化。

方案不能自行创造世界内核中不存在的物理作用。所谓“毒素”“能量抽吸”“信号腺体”都要求世界预先提供对应执行器、守恒和冲突语义。

因此应称为“无预设角色”，而不是“无预设功能基底”。

## 3. 容量机制评估

### 3.1 优点

固定 `K_max`、实体有效 `K_i` 和掩码适合 SoA/GPU；容量成为可遗传表型并支付成本，也符合存在筛选。

### 3.2 问题

给出的映射：

```text
K = clip(floor(8 + 24g), 1, 32), g∈[-1,1]
```

会把较大的负基因区间全部压到容量 1，产生明显边界堆积；`floor` 还会制造不均匀的中性区和突变跳变。

单一 `K` 也会把工作记忆、长期知识、关系容量、传感容量和模块数量压成一个维度，不利于真正分化。

### 3.3 建议原则

分离：

- 遗传最大容量；
- 发育建成容量；
- 当前激活容量；
- 实际占用量。

分别允许工作记忆、知识、关系、传感和储存容量演化，并区分结构成本、使用成本、发育成本和机会成本。

## 4. 代谢成本评估

`αK + βK²` 可以作为实验性成本曲线，但不是天然的“物理代谢因果律”。若参数未经世界能量尺度校准，它会直接预设复杂度选择方向。

只收能量税还可能把多维权衡重新压成单轴。更合理的科学约束包括：

- 能量维护；
- 材料/质量占用；
- 发育时间；
- 移动负担；
- 修复难度；
- 繁殖投入；
- 实际调用成本。

高容量能否获益必须由环境、信息限制和实际使用决定，不能写成必然结果。

## 5. 通用功能算子评估

### 5.1 优点

固定批量算子、遗传门控和路由能避免动态代码，并保持统一观察—行动接口、可审计性和消融能力。

### 5.2 概念边界

“新器官只是状态到响应的映射”过于简化。器官还涉及：

- 物理位置和形态；
- 感知范围和遮挡；
- 功率、质量和材料；
- 损伤和修复；
- 发育和复制；
- 与环境的真实交互端口。

纯 action residual 更接近“新控制通路”，不自动等于新器官。

### 5.3 路由限制

Softmax 输出路由只允许正权重且总和为 1，会限制：

- 抑制性通路；
- 多个独立输出；
- 完全不路由；
- 输出预算随表达改变。

需要显式的符号、预算、稀疏性和关闭语义。

## 6. 示例代码问题

示例仅适合作为概念草图，不能直接实施。

### 6.1 Output router 实际失效

代码将：

```text
module_outputs: [N,M,8]
router:         [N,M,8]
```

扩展为外积 `[N,M,8,8]`，随后又对 router 所在轴求和。因为 softmax 在该轴上的和恒为 1，最终输出基本退化为原 `module_outputs` 的求和，`output_routers` 不产生所描述的路由作用。

### 6.2 初始门控并未关闭

零初始化经过 sigmoid 后为 0.5，因此：

- expression gate 默认半开启；
- input selector 默认选择每个输入的 0.5；
- output router 默认均匀分布。

这与“未表达模块”不一致。

### 6.3 `active_mask` 未使用

函数接收 `active_mask`，但没有应用它；死亡或无效槽位仍会参与计算并产生税费输出。

### 6.4 Bitwise exact 声明不成立

CuPy 的浮点 sigmoid、softmax、einsum 和并行归约不因“纯张量”就自动与 CPU 位级一致。需要量化整数、固定归约、明确舍入/饱和和设备 parity 证明。

### 6.5 计算成本与代谢成本不一致

若所有实体始终计算全部最大模块和槽位，再通过 mask 丢弃，实际 GPU 计算成本并未随有效容量降低。项目可以人为收取代谢成本，但必须明确它是模型成本，不是设备实际耗时的直接映射。

## 7. 基因重复与新功能化评估

### 7.1 可保留部分

- 复制到固定空槽；
- 保存模块同源来源；
- 复制后允许路由和权重分化；
- 支持模块失活和删除；
- 用消融验证功能。

### 7.2 需要修改部分

“复制模块自动获得更高突变率”会人为提高复制路线的创新优势。应把它设为可选实验机制，或让突变稳定性本身演化并支付成本。

“Epigenetic Switching”命名不准确：繁殖时随机翻转遗传 gate 是遗传表达突变，不是表观遗传。表观遗传需要与序列分离、环境响应和有限跨代继承。

复制还应承担：

- 剂量效应；
- 结构和发育成本；
- 槽位占用；
- 输入和执行器竞争；
- 删除、退化和假基因化。

## 8. 推荐采纳方式

不原样采纳完整方案，而是拆成四个独立、可消融阶段：

1. **Elastic capacity**：先实现多类容量与分层成本；
2. **Expression/routing modules**：在现有物理接口内允许组合功能；
3. **Duplication/deletion lineage**：加入复制、删除和同源审计；
4. **Embodied modules**：让模块控制真实传感、储存、转化、信号和连接端口。

每阶段均与固定容量/无复制/无重联对照，不与社会控制同时引入。

## 9. 进入社会阶段前的验收

只有满足以下条件，才建议恢复社会主体为实现主线：

- 环境不再近似单一轴；
- 存在可遗传且有成本的表型差异；
- 至少两类生态型具有条件性优势或稳定共存；
- 功能组合可通过模块同源和消融验证；
- 分化不是由中性基因、初始聚类或自动多样性保护制造；
- 同质实体对照不能产生相同社会结构。


## v0.52 conservation note

The v5 architecture is retained. The supplied long-run result exposed a settlement bug rather than a missing trait: negative energy was allowed to create negative messenger flows. New v3 physiology semantics correct only substrate accounting and preserve v2 for exact replay. No new role, module, organ, or ecology actor is added.

## v0.53 resource buffering assessment

The conservative physiology substrate is retained. The next limitation was not another missing module output but immediate settlement of all harvested channels into body outcomes. D3-A adds inherited bounded stores and delayed conversion while preserving the fixed operator kernel, existing resource-effect matrix, and equal base parameters across channels.

This creates a temporal processing axis and exposes internal inventory to operator input selection. It does not yet add spatial processing sites, detritus, trophic transfer, or a claim of metabolic specialization.


## v0.107 分区统一主体图补充评估

通用功能算子、遗传重复和表达门控仍是可复用基础，但不应把所有节点初始化为一个完全无结构的统一池。为缩短有效结构的演化搜索时间，主体图采用预设计算区域；区域内连接、更新频率和状态容量提供发育偏置，跨区边负责功能整合。

这不改变原评估中的语义边界：通用算子不能自行创造新的世界能力，也不能通过节点名称创造利益、信任或社会角色。区域只能规定计算条件，不能规定认知内容。

推荐实现顺序为：固定容量与 disabled-neutral 存储、前向激活路由、客观 usage trace 与延迟可塑性、发育和成本、最后才是长期演化与中和实验。不得在第一版中同时开放任意拓扑、生命周期结构学习和完整 GPU 动态图。
