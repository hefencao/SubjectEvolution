# 数据结构规范

版本：v0.2  
目标：支持CPU参考实现、单GPU大规模运行及未来强化学习扩展。

---

## 1. 数据设计原则

1. 稳定ID与数组位置分离。
2. GPU主数据使用Structure of Arrays（SoA）。
3. 动态变长数据使用固定容量槽位、分块池或CSR快照。
4. 策略参数与主体状态分离。
5. 客观世界状态与主观观察分离。
6. 所有消息、观察和行动携带时间与有效性信息。
7. 所有随机结果可通过随机键追踪。
8. 分析数据不得成为策略隐式输入。

---

## 2. 基础类型

建议统一使用：

```cpp
using EntityId = uint64_t;
using SubjectId = uint64_t;
using RelationId = uint64_t;
using PolicyId = uint32_t;
using Tick = uint64_t;
using TypeId = uint16_t;
using ModuleMask = uint32_t;
```

约定：

- `0`为无效ID；
- ID生成只保证唯一，不编码类型、位置或出生顺序；
- GPU数组索引使用32位整数；
- ID到数组索引通过哈希表或稠密映射维护；
- 不允许策略通过ID数值推断隐藏信息。

---

## 3. 物理实体SoA

```text
PhysicalEntityArrays
{
    entity_id[N]             : uint64
    alive[N]                 : uint8
    generation[N]            : uint32
    type_id[N]               : uint16

    position_x[N]            : float32
    position_y[N]            : float32
    velocity_x[N]            : float32
    velocity_y[N]            : float32
    radius[N]                : float32
    mass[N]                  : float32

    energy[N]                : float32
    integrity[N]             : float32
    temperature[N]           : float32
    storage_used[N]          : float32
    storage_capacity[N]      : float32

    module_mask[N]           : uint32
    module_params[N][M]      : float16/float32

    primary_subject_id[N]    : uint64
    social_subject_id[N]     : uint64
    lineage_subject_id[N]    : uint64

    policy_id[N]             : uint32
    policy_version[N]        : uint32
    memory_slot[N]           : uint32

    birth_tick[N]            : uint64
    death_tick[N]            : uint64
}
```

### 3.1 双缓冲字段

以下字段应使用前后缓冲或快照：

- 位置、速度；
- 能量、完整度；
- 连接状态；
- 动态场；
- 公开社会状态。

策略读取只读快照，不能在观察阶段读取正在写入的新状态。

### 3.2 数值精度

- 空间位置、能量和关键统计默认`float32`；
- 神经网络推理可使用`float16/bfloat16`；
- 累积资源、全局归约和实验指标应使用`float64`或补偿求和；
- 不允许用低精度保存主体ID、时间戳和随机键字段。

---

## 4. 模块数据

固定模块槽位：

```text
ModuleSlots
{
    module_type[N][S]        : uint16
    module_enabled[N][S]     : uint8
    health[N][S]             : float32
    activation[N][S]         : float32
    maintenance_cost[N][S]   : float32
    custom_params[N][S][P]   : float16/float32
}
```

建议第一版：

- `S = 8`或`12`；
- `P = 4`或`8`；
- 不存在模块使用掩码关闭；
- 模块类型不得改变数组布局。

---

## 5. 候选主体数据

候选主体不要求与物理实体一一对应。

```text
CandidateSubjectArrays
{
    subject_id[NS]               : uint64
    active[NS]                   : uint8
    subject_kind[NS]             : uint16
    update_period[NS]            : uint32
    next_update_tick[NS]         : uint64

    policy_id[NS]                : uint32
    policy_version[NS]           : uint32
    memory_slot[NS]              : uint32
    lineage_id[NS]               : uint64

    persistence_score[NS]        : float32
    causal_control_score[NS]     : float32
    boundary_score[NS]           : float32
    integration_score[NS]        : float32
    external_drive_score[NS]     : float32

    public_state[NS][PS]         : float32
}
```

成员、承载体和层级关系使用独立边表。

---

## 6. 主体图边

### 6.1 通用边结构

```text
SubjectEdge
{
    source_subject_id
    target_subject_id
    edge_type
    weight
    confidence
    created_tick
    last_update_tick
    flags
}
```

`edge_type`至少包括：

- `SUBSTRATE_OF`
- `MEMBER_OF`
- `PARENT_OF`
- `DESCENDS_FROM`
- `CONTROLS`
- `DEPENDS_ON`
- `SHARES_MEMORY_WITH`
- `COMPETES_WITH`
- `COOPERATES_WITH`

### 6.2 GPU存储

运行时使用：

- 高频固定关系：固定容量槽位；
- 低频主体图：CPU或GPU CSR快照；
- 跨区域长连接：压缩摘要；
- 图更新：先写入增删缓冲区，再批量重建。

---

## 7. 个体重要关系

```text
RelationSlots
{
    target_id[N][K]              : uint64
    relation_type[N][K]          : uint8
    trust[N][K]                  : float16
    familiarity[N][K]            : float16
    kinship_estimate[N][K]       : float16
    debt[N][K]                   : float16
    signal_reliability[N][K]     : float16
    last_interaction_tick[N][K]  : uint32
    valid[N][K]                  : uint8
}
```

建议`K=16`起步。

关系槽位替换策略必须显式规定，例如：

\[
priority =
w_1\cdot familiarity+
w_2\cdot trust+
w_3\cdot recency+
w_4\cdot dependency
\]

关系容量限制属于世界认知机制，必须进入实验配置。

---

## 8. 信息与消息

### 8.1 原始信号

```text
SignalEmission
{
    emission_id
    source_entity_id
    source_subject_id
    channel_type
    payload_type
    payload_vector[P]
    encoded_confidence
    intentional_deception
    power
    origin_x
    origin_y
    emit_tick
    ttl
    random_key
}
```

### 8.2 接收事件

```text
SignalReception
{
    emission_id
    receiver_entity_id
    receiver_subject_id
    receive_tick
    channel_delay
    measured_strength
    decoded_payload[P]
    estimated_confidence
    source_estimate
    detection_success
    corruption_flags
    random_key
}
```

### 8.3 信号场

规则网格通道：

```text
FieldGrid
{
    field_value[C][GX][GY]
    field_age[C][GX][GY]
    field_source_mix[C][GX][GY]
}
```

需要双缓冲，并显式处理扩散、衰减、遮挡和叠加。

---

## 9. 观察结构

```text
ObservationBatch
{
    subject_ids[B]

    self_features[B][FS]
    local_environment[B][FE]
    sampled_neighbors[B][K][FN]
    received_messages[B][M][FM]
    relation_summary[B][FR]
    memory_features[B][FH]

    feature_mask[B][F]
    neighbor_mask[B][K]
    message_mask[B][M]

    observation_tick[B]
    oldest_input_tick[B]
    estimated_uncertainty[B][FU]
}
```

要求：

- 固定最大长度；
- 使用掩码；
- 明确区分未观察、观察为零和数据过期；
- 不允许包含全局真实统计，除非通过合法公共信息渠道获得。

---

## 10. 策略与记忆

### 10.1 策略注册

```text
PolicyRegistryEntry
{
    policy_id
    policy_kind
    parameter_offset
    parameter_length
    input_schema_version
    action_schema_version
    trainable
}
```

### 10.2 个体记忆

```text
MemoryPool
{
    memory_state[NM][H]
    owner_subject_id[NM]
    memory_type[NM]
    last_update_tick[NM]
}
```

网络参数不得复制到每个主体。个体差异通过：

- 遗传潜变量；
- 记忆；
- 模块；
- 小量调制参数；
- 策略版本。

---

## 11. 行动提案与控制贡献

```text
ControlProposal
{
    proposal_id
    proposing_subject_id
    carrier_entity_id
    action_type
    target_id
    parameters[A]
    action_logits[L]
    requested_control
    valid_until_tick
    random_key
}
```

仲裁后生成：

```text
ActionIntent
{
    intent_id
    carrier_entity_id
    resolved_action_type
    target_id
    parameters[A]

    contribution_count
    contributor_subject_ids[C]
    contribution_weights[C]

    sampled_probability
    execution_priority
    submit_tick
}
```

最终执行记录：

```text
ActionResolution
{
    intent_id
    success
    failure_reason
    executed_parameters[A]
    energy_cost
    integrity_change
    resource_delta
    resolve_tick
    random_key
}
```

必须同时保留“选择、意图、执行、结果”四层信息。

---

## 12. 出生、死亡与复制事件

```text
BirthRequest
{
    parent_entity_ids[]
    parent_subject_ids[]
    offspring_type
    genotype_source
    requested_position
    resource_commitment
    mutation_key
}
```

```text
DeathEvent
{
    entity_id
    primary_subject_id
    death_tick
    cause_code
    final_energy
    final_integrity
}
```

```text
ReplicationEvent
{
    source_subject_id
    target_carrier_id
    lineage_id
    replication_kind
    fidelity
    success
}
```

出生请求先缓冲，统一分配槽位。死亡先标记，阶段末批量清理。

---

## 13. 轨迹和回放

```text
TrajectoryRecord
{
    run_id
    tick
    subject_id
    entity_id

    observation_ref
    policy_id
    policy_version
    memory_before_ref

    action_logits
    sampled_action
    sample_probability
    action_intent_ref
    action_resolution_ref

    memory_after_ref
    objective_world_delta
    membership_snapshot
    random_keys[]
}
```

轨迹分三级：

- L0：全局统计；
- L1：主体摘要；
- L2：抽样完整轨迹。

禁止默认永久保存所有实体每步完整状态。

---

## 14. 版本兼容

每类数据必须带：

- schema版本；
- 配置哈希；
-策略版本；
-世界规则版本；
-采样API版本。

存档加载时：

- 版本完全一致：直接加载；
- 可迁移版本：显式迁移；
- 不兼容版本：拒绝加载，不允许静默解释。

---

## 15. 最小容量建议

100,000实体MVP建议：

| 数据 | 建议 |
|---|---:|
| 物理实体容量 | 131,072 |
| 候选主体容量 | 262,144 |
| 每实体模块槽 | 8 |
| 每实体关系槽 | 16 |
| 每观察邻居上限 | 32 |
| 每观察消息上限 | 16 |
| 每行动贡献主体上限 | 4 |
| 主体图边初始容量 | 1,000,000 |
| 完整轨迹抽样主体 | 100–1,000 |

---

## 16. 数据结构验收

必须满足：

- 圆球与主体ID独立；
- 相同策略可服务大量主体；
- 普通策略可替换为RL策略；
- 所有消息含时间与置信度；
- 所有随机结果可定位到随机键；
- 主体图允许跨圆球和跨世代；
- 出生死亡不需要单对象动态分配；
- 观察不泄漏世界真值；
- CPU和GPU实现可交换同一逻辑测试数据。
