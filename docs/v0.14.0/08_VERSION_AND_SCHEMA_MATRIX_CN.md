# 版本、Schema 与兼容性矩阵

## 1. 核心版本矩阵

| 版本 | Knowledge schema | Policy/Router | 关键能力 |
|---|---|---|---|
| K1/v0.5 | `dynamic-knowledge-k1-v1`（历史） | 原遗传策略 | 副本、容量、成本、交换、损坏 |
| K2/v0.6 | `dynamic-knowledge-k2-v1` | `inherited-linear-policy-v1` | 五维局部后果，不影响策略 |
| K3/v0.7 | K3 知识 | `inherited-linear-policy-knowledge-residual-v1` | 稀疏 outcome residual |
| K4/v0.8 | `dynamic-knowledge-k4-v1` | K3 policy | 内容谱系和候选主体诊断 |
| v0.10 L1 | `dynamic-knowledge-latent-v1` | `quantized-linear-latent-router-v1` | 变长 latent、线性路由 |
| v0.11 L2 | 同上 | `quantized-mlp-latent-router-v1` | 两层 MLP、hard-tanh、L1 shadow |
| v0.12 | 同上 | L1/L2 + `latent-routing-compute-cost-v1` | 真实计算成本和预算 |
| v0.13 | 同上 | L2 + `quantized-working-memory-v1` + `sparse-query-key-topk-router-v1` | 工作记忆、stable Top-k |
| v0.14 | 同上 | v0.13 + `inherited-discrete-topk-v1` | 实体级遗传容量和消融 |

## 2. 基因组隔离

| 路径 | 已知基因组宽度 | 说明 |
|---|---:|---|
| K1/K2 | 136 | 旧策略语义保持 |
| K3 | 142 | 追加五维 outcome preference 和 use strength |
| L1 | 246 | 追加量化线性潜路由 |
| L2 | 446 | 保留 L1 前缀，再追加 MLP 参数 |
| v0.13 memory/top-k | 依配置扩展 | 工作记忆和 Query 参数仅在显式 schema 中追加 |
| v0.14 inherited Top-k | 在 v0.13 基础上追加 1 个容量基因 | 固定 K 配置不追加 |

最后两项的精确总宽度应由当前 `config.py/policy.py` schema 解析结果为准，不要在外部代码中硬编码。

## 3. 当前 v0.14 关键 schema

```text
policy.schema = inherited-variable-latent-router-mlp-v1
knowledge.schema = dynamic-knowledge-latent-v1
latent_schema = variable-latent-knowledge-v1
latent_router_schema = quantized-mlp-latent-router-v1
policy_residual_schema = quantized-variable-latent-mlp-residual-v1
routing_cost_schema = latent-routing-compute-cost-v1
routing_budget_mode = all-or-none-per-entity-v1
working_memory_schema = quantized-working-memory-v1
sparse_selection_schema = sparse-query-key-topk-router-v1
sparse_selection_capacity_schema = inherited-discrete-topk-v1
```

## 4. 兼容性要求

新版本验收至少应比较：

- 非计时 metrics 共同字段；
- 事件/后果/贡献/成本/选择日志共同字段；
- checkpoint 共同数组；
- 基因组旧切片；
- 同 seed 动作、出生死亡和稳定 ID；
- full checkpoint 连续/恢复状态。

## 5. GPU 语义模式

| 模式 | 含义 | 科学状态 |
|---|---|---|
| `strict-reference` | 需要可用 GPU，但世界采用 CPU reference 语义 | 正式正确性门禁 |
| `hybrid-accelerated` | 实验设备世界路径 | v0.14 真实 CUDA parity 待验 |

## 6. Checkpoint schema

完整恢复格式：`subject-evolution-full-checkpoint-v1`，扩展名 `.sechk`。包含 pickle，必须视为可信项目内部文件，不是安全的第三方交换格式。
