# K3 实现说明：稀疏知识策略残差（v0.7.0）

## 阶段边界

K3 在 K2 的局部多维后果统计上增加知识对策略 logits 的稀疏残差，但保持以下边界：

- 旧 `inherited-linear-policy-v1` 的 128 个策略权重含义不变；
- K1/K2 配置继续使用 136 维基因组；
- 只有显式启用 `inherited-linear-policy-knowledge-residual-v1` 的 K3 配置使用 142 维基因组；
- 知识不绕过 observation → proposal → intent → resolution → commit；
- 不读取未来、全局适应度或集中回报；
- 五维 outcome 不压缩成系统预设的单一奖励。

## 策略组合

K3 的动作 logits 为：

```text
action_logits = genetic_prior_logits + sparse_knowledge_residual
```

遗传层新增六个慢变量：

1. energy outcome preference；
2. integrity outcome preference；
3. material/resource outcome preference；
4. information outcome preference；
5. reproduction-opportunity preference；
6. knowledge use strength。

这六个性状只存在于 K3 schema，位于旧 136 维基因组之后。旧策略权重仍严格位于原切片中。

## 稀疏 KnowledgePolicyPlan

每个 tick 以已发布的 `KnowledgeObservationPlan` 为输入，按 holder、当前 local context 和 action 匹配副本，生成不可变 `KnowledgePolicyPlan`：

- `active_rows`；
- `entity_ids` / `holder_subject_ids`；
- `context_keys` / `action_ids`；
- `residuals`；
- 私有、交换、未验证交换支持数；
- reliability mass；
- reliability-weighted 五维 outcome。

重复副本使用可靠性加权均值合并，不允许通过复制同一内容无限放大 residual。最终 residual 经过显式 outcome scale、clip 和最大绝对 logit residual 限制。

## 外来知识

接收但尚未本地验证的交换知识不会被伪装成已验证知识。其行为影响由配置项 `policy_unverified_transfer_weight` 显式折扣；K2 的本地验证规则不变。没有 outcome 样本的种子副本不会形成 residual。

## 可审计贡献

`PolicyDecision` 现在可携带：

- `genetic_logits`；
- `knowledge_logits`；
- `genetic_action`；
- 最终 action。

使用同一 counter-based 随机抽样比较 genetic-only 与 combined logits，从而统计知识是否实际改变动作，而不是只报告 residual 非零。

可选日志 `knowledge_policy_contributions.csv` 逐条记录 holder、context、action、residual、支持来源、可靠性质量和五维 outcome。metrics 输出累计影响实体数、action cell 数、改变动作数、residual 绝对和及知识使用性状统计。

## GPU 路径

K3 的 hybrid GPU 路径不上传完整 `entity × action` 矩阵。CPU 端从动态知识 arena 构建稀疏计划，只上传非零 `(active_row, action_id, residual)`，随后在设备 logits 上提交。K2 的 information/harvest reference-order parity 修复继续保留。

当前执行容器没有 CUDA，因此 K3 的真实 CuPy 多 tick parity 尚未在本轮本地验证。K2 hybrid parity 已由用户在 `mvp_short_k2_exchange` 上验证至 tick 1000 无偏差。

## 未包含

K3 不实现：

- 知识内容作为候选主体进入主体图（K4）；
- 信息模板寄生主体；
- Hero 强化学习；
- 完整主体性评分；
- 任意信息通道 schema；
- 完整设备驻留世界循环。
