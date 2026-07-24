# L2 非线性潜知识路由器实现（v0.11.0）

## 目标

v0.11.0 在 v0.10.0 的可变长度潜知识 L1 线性路由器之上，新增独立的 L2 schema：

```text
variable latent content
+ local five-dimensional outcomes
+ public carrier state
+ reliability/source metadata
→ inherited quantized two-layer MLP
→ public action-logit residual
```

L2 不引入外部训练器、全局 reward、反向传播或未来信息。全部路由参数仍是承载体基因组的一部分，只通过出生继承与既有突变机制变化。

## Schema 隔离

| 层 | L1 | L2 |
|---|---|---|
| Knowledge | `dynamic-knowledge-latent-v1` | `dynamic-knowledge-latent-v1` |
| Router | `quantized-linear-latent-router-v1` | `quantized-mlp-latent-router-v1` |
| Policy | `inherited-variable-latent-router-v1` | `inherited-variable-latent-router-mlp-v1` |
| Residual | `quantized-variable-latent-residual-v1` | `quantized-variable-latent-mlp-residual-v1` |
| Genome width | 246 | 446 |

L2 基因组保留完整的 104 个 L1 路由基因作为前缀，随后追加 200 个 MLP 基因。旧 128 个遗传策略权重、五个 K3 后果偏好和 knowledge-use-strength 的索引均未改变。

## 网络结构

默认参数：

- 内容长度等级：4、8、16、32；
- 固定潜投影宽度：8；
- 公开承载体状态：4 维（energy fraction、integrity、fertility、scarcity）；
- 路由元数据：3 维（reliability、transfer source、unverified transfer）；
- MLP 输入宽度：15；
- MLP 隐层宽度：8；
- 输出宽度：8 个 action logits。

第一层和第二层均使用 inherited int16 权重。激活为规范化整数 hard-tanh：

```text
h = clip(pre_activation_q, -activation_clip_q, +activation_clip_q)
```

不调用 `tanh`、`exp` 或后端相关近似函数。

## CPU/GPU 数值语义

五维后果、公开状态、可靠性、来源标志和 knowledge-use-strength 在公开边界量化。变长潜投影、两层路由与副本聚合均使用有界整数运算。

为避免 GPU contraction 顺序影响离散动作：

- 关键乘加按固定输入/隐藏维度顺序执行；
- holder/action 副本归约使用整数加法；
- 最终 residual 量化后再进入 policy；
- L1 shadow 与 L2 使用同一 latent batch 和同一 counter-based action draw。

真实 CuPy/CUDA 多 tick parity 尚未在当前容器验证。正式 GPU scientific run 仍应使用 `strict-reference`。

## L1 影子路由

L2 每 tick 同时计算：

1. 纯遗传策略动作；
2. 保留的 L1 线性路由动作；
3. L2 非线性路由动作。

L1 只作为诊断影子，不参与 L2 世界提交。这样可以在同一个 L2 世界状态和同一个随机抽样下记录：

- genetic → L2 action changes；
- L1 shadow → L2 action changes；
- L1 和 L2 每个 action 的量化 residual。

## 审计

`knowledge_policy_contributions.csv` 新增：

- `linear_shadow_logit_residual`；
- `linear_shadow_quantized_residual`；
- `router_saturation_count`；
- `router_clipping_count`；
- `router_hidden_abs_sum`；
- `router_hidden_active_count`。

内部设备/CPU 诊断还保留每个匹配副本的：

- 公共潜投影；
- 第一层 pre-activation；
- hard-tanh 后隐藏向量；
- 每 action 输出裁剪标志。

这些诊断不参与 policy、intent、resolution 或 commit。

## 成本与容量

L2 复用 v0.10.0 的真实长度成本：

- 存储成本随 latent length 增长；
- 传播成本按实际 encoded bytes；
- 维持成本按实际 bytes；
- 损坏变体可以扩展或收缩长度；
- 接收容量在变体落地前按实际目标长度仲裁。

当前 MLP 计算成本只作为路由诊断量记录，尚未转化为新的物理能量费用；这是后续预算实验需要显式控制的变量。

## 未完成范围

- 真实 CUDA L2 world parity；
- 持久 device-resident latent buckets；
- MLP 计算能耗的物理结算；
- 潜坐标或路由器的副本内局部学习；
- 任意连续长度和运行时 JIT；
- 长期、多 seed 适应优势证明。
