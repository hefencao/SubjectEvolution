# K2 实现说明：局部后果记录与知识副本经验更新

## 1. 阶段边界

本版本实现 `dynamic-knowledge-k2-v1` 与 `local-outcome-v1`。K2 继续保持
`inherited-linear-policy-v1` 不变：知识不会进入 policy features、logits、control proposal、
intent 或 action conflict resolver。K2 只观察当前 tick 已提交的本地物理后果，并更新持有者
自己的知识副本统计。

没有全局 reward、未来状态、种群适应度、集中优化器、参数同步或反向传播。

## 2. `KnowledgeOutcomePlan`

每个旧有承载体在 action conflict 完成后保存提交前快照，并在下列提交完成后生成不可变后果计划：

1. movement；
2. harvest；
3. share；
4. signal 与 K1 知识传输成本；
5. reproduction 成功后的父代能量与 fertility 成本。

后果快照在基础维持成本、移动成本、环境 hazard、衰老和死亡结算之前发布。因此该向量表示
**行动局部结算后果**，不把所有环境变化错误归因给当前动作。

计划字段包括：

```text
tick, carrier_index, entity_id, holder_subject_id,
context_key, action_id, status, failure_reason, outcome_vector
```

`status` 区分失败、成功和部分成功。当前部分成功判定覆盖：

- harvest 得到正资源但低于配置请求量；
- share 实际提交量低于发送者当时可提出的量。

## 3. 五维后果向量

`local-outcome-v1` 固定顺序为：

```text
[energy_delta,
 integrity_delta,
 material_delta,
 information_delta,
 reproduction_opportunity_delta]
```

- `energy_delta`：行动提交后的 carrier energy 减去提交前 energy；
- `integrity_delta`：行动提交后的 integrity 变化；
- `material_delta`：harvest 实际取得的四类资源量之和；
- `information_delta`：`information_store` 的变化；
- `reproduction_opportunity_delta`：连续机会量的变化，定义为
  `min(clamp(energy / reproduction_threshold), clamp(fertility / 0.5))`。

向量不会压缩成单一“好/坏”或 reward。

## 4. `local-context-v1`

上下文只使用当前承载体的本地观察：

- 当前格主资源；
- 当前格 hazard；
- 自身 energy / max_energy；
- 自身 integrity；
- 是否处于候选群组。

前四项使用三个粗粒度 bin，群组状态使用一位。组合结果是稳定的正整数 `context_key`。
该编码不读取未来、全局均值或其他承载体的适应度。

## 5. 副本本地统计

`KnowledgeArena` 新增与副本一一对齐的 SoA 数组：

```text
outcome_mean[copy, 5]
outcome_m2[copy, 5]
acquisition_kind[copy]
```

`outcome_mean` 和 `outcome_m2` 使用 Welford 增量统计；`sample_count` 只表示该持有者自己的
匹配经验次数。更新顺序按 holder subject ID、entity ID 和 copy ID 规范化，避免输入排列改变结果。

一个 outcome 默认只更新最旧的一个匹配副本（`max_updates_per_outcome=1`）。该规则不查看
后果大小、置信度或所谓“正确性”。

置信度更新为：

```text
confidence += confidence_learning_rate * (1 - confidence)
```

可配置的 `confidence_decay_per_tick` 在维持阶段显式衰减置信度。

## 6. 私有经验创建

若 holder 没有匹配 `context_key + action_id` 的副本，可创建新的私有经验内容和副本：

- 新内容为不可变目录项；
- `source_subject_id` 为 holder；
- `sample_count=1`；
- `last_verified_tick` 为当前 tick；
- `acquisition_kind=private-experience`；
- 初始 outcome mean 就是实际亲历后果。

默认 `experience_creation_requires_free_capacity=true`。容量已满时拒绝新经验，不为了新经验
暗中淘汰已有知识。配置允许关闭此限制；若关闭，仍只使用 K1 的 `oldest-copy-v1` 淘汰规则。

## 7. 交换知识的验证

K1 有代价传输继续工作。传输计划现在携带发送副本的本地 outcome mean、confidence 和
source sample count，用于可审计复制。

接收副本满足：

- `sample_count=0`，因为接收者尚未亲历；
- `last_verified_tick=0`；
- `acquisition_kind=transfer`；
- confidence 受到 receiver noise 衰减；
- outcome mean 初始化为发送副本的当前本地统计。

同一 tick 新接收的副本不会用导致该传输的同一动作自我验证。只有后续 tick 中接收者亲历
匹配 context/action 后，才增加本地 sample count、confidence 和 last verified tick。

传播损坏会基于发送副本的最新本地 outcome 创建不可变变体，并保留 `parent_content_id`。

## 8. 成本与审计

K2 新增 `verification_energy_cost`。每次成功更新或创建一个经验副本都支付一次验证成本；
能量不足则拒绝更新并计数。该成本与 K1 的存储、发送和接收成本分别统计。

新增输出：

- `knowledge_outcome_updates.csv`：逐个成功更新/创建事件；
- `knowledge_events.jsonl` 中的 `outcome-summary`；
- metrics 中的 outcome、更新、私有经验、交换验证、拒绝和学习成本字段；
- checkpoint 中的 `knowledge_copy_outcome_mean`、`knowledge_copy_outcome_m2` 和
  `knowledge_copy_acquisition_kind`；
- run manifest 与 scientific validity 中的 K2 schema 和 `knowledge_policy_influence=false`。

## 9. 未包含在 K2 中

- 知识对 logits 或行动的任何影响（K3）；
- 知识谱系进入候选主体图（K4）；
- 完整 checkpoint 世界恢复接口；
- 离线反事实重放；
- Hero 强化学习；
- 任意信息通道 schema；
- 完整 GPU 驻留世界循环。
