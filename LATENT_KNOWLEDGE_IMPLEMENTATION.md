# 可变长度潜知识与可演化路由器（v0.10.0）

## 阶段边界

本阶段实现高扩展路线的 L1 基线：

```text
可变长度潜知识内容
+ 承载体局部五维后果
+ 遗传编码的量化线性路由器
→ 公开的 action-logit residual
```

潜知识不能绕过 policy → intent → resolution → commit，也没有独立执行器。这里限制的是隐藏的外部控制路径，而不是潜变量表示。路由器参数来自实体基因；潜内容来自世界内部的内容创建、局部经验与传播变体；不存在集中训练器、全局 reward 或反向传播。

## 独立 schema

- knowledge schema：`dynamic-knowledge-latent-v1`
- latent payload schema：`variable-latent-knowledge-v1`
- policy schema：`inherited-variable-latent-router-v1`
- router schema：`quantized-linear-latent-router-v1`
- residual schema：`quantized-variable-latent-residual-v1`

K1–K4 和 K3 固定五维 residual 默认不启用该路径。

## 权威存储

`VariableLatentContentStore` 使用变长 SoA：

```text
length[content]
offset[content]
values[total_dimensions]  # int16
```

内容长度从离散等级选择，当前默认：

```text
4, 8, 16, 32
```

这些是 GPU 批处理等级，不是预设语义类别。类别语义可以根据潜表示、内容谱系、行为贡献和反事实消融后验分析。

## 长度演化

根内容可落入不同长度等级。损坏传播产生的变体按显式概率在相邻长度等级扩展或收缩：

```text
latent_length_mutation_probability = 0.125
```

扩展的新坐标由固定 seed、父子内容 ID 和维度确定性生成；收缩保留规范前缀。长度会改变：

- 副本编码字节；
- 宿主容量占用；
- 维持成本；
- 传播与接收成本；
- GPU 路由工作量。

损坏变体在提交前预演真实落地长度，容量仲裁按落地字节执行，避免先通过容量检查后再扩张。

## 个体化有效表示

潜 payload 属于内容谱系，K2 的副本局部五维后果仍属于副本。策略时将局部后果按固定投影注入潜隐藏表示，因此相同内容在不同宿主上的局部验证历史可以产生不同有效解释，同时不修改共享内容本体。

## 遗传线性路由器

旧 128 个策略权重语义不变。潜 schema 的基因组包括：

- 原有 morphology + 128 个策略权重；
- 五维 outcome preference 与 knowledge use strength；
- 每个动作的 latent-hidden 权重；
- 每个动作的四维公开状态权重；
- 每个动作的 bias。

默认 hidden width 为 8，基因组宽度为 246；K3 仍为 142，K1/K2 仍为 136。

L1 使用 clipped-linear gene mapping。L2 非线性路由器尚未实现，并将使用独立 schema。

## GPU 计算视图

每个 tick 按潜长度生成桶：

```text
LatentBucket(width, batch_rows, values[K, width])
```

各桶在 NumPy/CuPy 上批量执行：

1. 变长 payload → 固定 hidden width；
2. 注入量化后的本地五维后果；
3. 与承载体遗传路由权重、四维局部状态组合；
4. 生成每副本、每动作整数贡献；
5. 按 holder/action 聚合；
6. 发布稀疏 `KnowledgePolicyPlan`。

当前权威 arena 仍在 host，GPU 桶每 tick 从 host materialize；持久设备驻留的变长 arena 尚未实现。

## CPU/GPU parity 契约

为避免微小浮点差异改变离散动作，公开边界采用量化：

- 五维后果在 CPU reference 归一化并量化；
- 四维承载体状态在 CPU reference 量化；
- knowledge-use strength 在 CPU reference 量化；
- router genes 采用 power-of-two scale 的 clipped-linear 量化；
- 大型变长投影和路由使用整数运算；
- 发布 residual 为规范化整数，再转换为 float32 策略接口；
- 最终贡献有稳定审计顺序。

v0.10.0 还修复了旧 hybrid GPU path 没有把已构造的 `knowledge_policy_plan` 传入 `policy.decide()` 的问题。当前环境没有 CUDA，真实 CuPy 多 tick parity 仍待 GPU 主机验证。

## 审计输出

`knowledge_policy_contributions.csv` 新增：

- `router_schema`
- `latent_dimension_count`
- `latent_max_width`
- `quantized_residual`

metrics/checkpoint 新增潜内容长度、offset、values、路由维数和量化 residual 统计。完整 `.sechk` 保存并恢复变长 store。

## 明确未实现

- L2 小型非线性路由器；
- 潜坐标的副本内局部梯度学习；
- 任意连续长度与运行时 JIT kernel；
- 持久设备驻留 latent arena；
- 动态信息通道 schema；
- 潜类别自然语言语义自动判定；
- 真实 CUDA 多 tick parity 证明；
- 潜知识带来长期适应优势的统计证明。
