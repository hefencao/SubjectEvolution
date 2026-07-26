# 科学问题与研究债务

本文件以 v0.28 代码、三个 seed 的 1500-tick 长跑、18-anchor manifest，以及用户提供的 72 个 checkpoint-immediate paired results 为准。“已实现”只表示机制、诊断或防护存在，不表示科学假设成立。

| ID | 状态 | 当前问题 | 下一步判据 |
|---|---|---|---|
| EXEC-01 | v0.25 结构完成 | manifest 绝对路径跨机器迁移可能破坏预注册信任链。 | 使用路径前缀映射并验证 progress、config、checkpoint SHA-256；任何 mismatch 停止。 |
| EXEC-02 | v0.25 结构完成 | 相同 checkpoint/干预的重复分支浪费算力。 | checkpoint-immediate 只能在 checkpoint、intervention 相同且 horizon 正确截断时共享。 |
| EXEC-03 | v0.28 修正 | 旧执行从 prior checkpoint 应用干预，会在名义事件前改变 exposure 和 cohort。72/72 pairs 提前 30/60 ticks，48/72 的 event alive 已不同。 | post-event 结论必须使用 shared prefix 到 event tick，再分支；旧结果明确标为 `checkpoint-immediate-v1`。 |
| EXEC-04 | v0.28 防护完成 | 不同 event tick 若共享同一已干预 trajectory，会把不同 intervention onset 合并。 | event-timed trajectory key 必须包含 event checkpoint/prefix；不同 event tick 不去重。 |
| EXEC-05 | v0.28 防护完成 | 人数相同不能证明 event cohort 身份相同。 | baseline/branch 的 global 与 regional stable-ID SHA-256 必须相同，pairing failure 必须为 0。 |
| SYNTH-01 | v0.28 v2 | 多批结果重复、覆盖不齐，人工拼表易产生伪重复。 | 只按 immutable anchor/intervention 合并；核心世界结果冲突时拒绝。 |
| SYNTH-02 | v0.28 防护完成 | checkpoint-immediate 与 event-timed 是不同估计量。 | synthesis 检测 timing mode；不同 mode 必须分开报告，禁止池化。 |
| SYNTH-03 | 开放 | 当前仅 72/108 checkpoint-immediate pairs，remaining-event knowledge plan 无 results。 | 优先完成三份 event-timed plans，不再用旧 timing 补齐覆盖。 |
| SCALE-01 | 开放 | scarcity exposure 接近饱和，不能与 crowding/mortality z-score 横向比较。 | 始终按 event kind 分层；必要时升级 exposure schema，而非事后调阈值。 |
| REPLICATION-01 | 防护完成 | 同一 seed 内两个 anchors 不是独立重复。 | 先 seed 内平均，再跨 seed 报方向；三 seed 不作显著性结论。 |
| CAUSAL-01 | 开放，边界更清晰 | 自然事件 exposure 未随机分配。 | event-timed branch 只识别自然事件状态形成后的机制效应，不声称 exposure 本身因果。 |
| CULTURE-01 | checkpoint-immediate 描述性复制 | 提前关闭传播后 active transferred roots 在三类事件中均下降。 | 需 event-timed 复制后才能称为“事件后的文化状态维持作用”；不得称人口、适应度或主体性收益。 |
| CULTURE-02 | 人口收益未建立 | commits 与 roots 是传播操作和文化状态，不是 demographic outcome。 | 只在 common event cohort 上解释 retained/absent/migration/birth 组件。 |
| CULTURE-03 | 开放 | transfer-off 后 new/lost roots 不必为零，因为既有 transferred roots 可迁移、消失或进入区域。 | future commits=0 是 manipulation check；root 指标只描述区域文化状态。 |
| GROUP-01 | 测量纠缠已识别 | freeze refresh 的 current-label cohesion 下降主要由评价分区改变。 | event-timed common-boundary 指标优先；current/common gap 只解释边界定义。 |
| GROUP-02 | 开放 | 冻结刷新改变标签陈旧度、新生体吸纳与 grouped fraction。 | 在共同 event state 上联合 common boundary、cohort、grouped fraction 和出生构成。 |
| COHORT-01 | v0.28 v2 | v0.27 每个分支各自冻结 cohort，不能保证是同一事件实体集合。 | 以 event checkpoint 分支并验证 stable-ID hashes。 |
| COHORT-02 | 开放 | endpoint decomposition 不是完整路径级 birth/death/migration ledger。 | 只有 event-timed endpoint 仍无法区分机制时才增加路径日志。 |
| COHORT-03 | 防护完成 | 槽位复用可能让新生实体继承 cohort 身份。 | stable entity ID 而非 slot 定义 cohort；测试覆盖槽位复用。 |
| AFFINITY-01 | 旧 timing 方向不可升级 | checkpoint-immediate neutralization 的 crowding alive 方向可能包含事件前迁移/出生变化。 | 运行 event-timed primary plan 后再分解共同 cohort。 |
| MEMORY-01 | 旧 timing 描述性 | working-memory ablation 的 crowding 结果已在事件前改变世界。 | event-timed crowding knowledge 复跑，并完成 mortality/scarcity。 |
| STRATEGY-01 | 覆盖未完成 | policy、memory、Top-k 只有 crowding checkpoint-immediate 结果。 | 三份 event-timed knowledge plans 完成后按事件和机制层级解释。 |
| DANGER-01 | 当前不可识别 | flagship 配置 danger evidence disabled。 | 继续标记 neutralization ineligible；仅在独立预注册启用配置评价。 |
| TRACE-01 | 机制完成，解释开放 | mortality trace 是实体死亡形成的局部证据，观察相关不等于适应价值。 | 在启用 inherited evidence mixture 的 paired event checkpoint 中评价。 |
| LINEAGE-01 | 开放 | 遗传世系、群组和文化状态可能共同受人口瓶颈驱动。 | 在相同 event checkpoint 对齐 lineage、文化和 cohort 组件。 |
| TIME-01 | 开放 | 世界 tick 不等于演化世代，120-tick horizon 不等于相同出生机会。 | 同时报告世代、出生量、有效谱系和共同 event cohort 组成。 |
| ENV-01 | 边界完成 | 生物型危险源会复制现有实体语义并混淆主体层级。 | 科学核心不新增第二套生命周期；合成移动场只作默认关闭插件。 |
| ENV-02 | 开放 | 信息通道仍固定为资源、危险、社会。 | 设计版本化任意信息通道 schema，保持旧配置/checkpoint 兼容。 |
| SUBJECT-01 | 开放 | 身体、谱系、社会和知识节点都是候选主体结构，不是主体性结论。 | 需要维持、边界修复、控制贡献和删除反事实多指标矩阵。 |
| SHIFT-01 | 开放 | 主体偏移不能写成实体状态或由单次依赖代理推出。 | 预注册 matched non-events 与跨尺度控制/物质流比较。 |
| GPU-01 | 未完成 | `hybrid-accelerated` 多 tick parity 尚未证明；用户运行是 `gpu-strict-reference`。 | 真实 CUDA 逐阶段定位首差异；科学运行继续 strict-reference。 |
| CHECKPOINT-01 | 已有防护 | `.sechk` 含 pickle，无法安全加载不可信来源。 | 只加载本项目可信输出；未来设计非可执行交换格式。 |
| REPRO-01 | 部分完成 | stateless capacity arbitration 修复 ID 偏差，但失败成本与同 tick 槽位释放仍是模型选择。 | 作为独立规则 schema 预注册，不静默修改。 |
| GENOME-01 | 开放 | 初代分布、突变率、固定形态槽和网络宽度约束可达空间。 | 做 schema-level sensitivity matrix，不把单组超参数稳定性当普遍规律。 |

## 当前解释边界

1. 三 seed 同号是描述性复制，不是统计必要性。
2. 自然事件 exposure 未随机化；event-timed paired branch 也不识别 exposure 本身因果。
3. checkpoint-immediate 与 event-timed 是不同估计量，禁止合并。
4. commits 与 roots 是机制近端指标，不等于人口、适应度或主体性。
5. current-label cohesion 对 group-refresh 干预存在定义耦合，应优先共同边界。
6. event cohort 只有在 stable-ID identity hashes 相同时才是共同 cohort。
7. endpoint cohort 分解不是完整路径流量或死亡时序。
8. 群组、谱系和知识候选图不能单独证明主体存在或主体偏移。
