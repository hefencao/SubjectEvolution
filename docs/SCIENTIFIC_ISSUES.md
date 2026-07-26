# 科学问题与研究债务

本文件以 v0.27 代码、三个 seed 的 1500-tick 长跑、18-anchor manifest，以及四份已执行 paired result 为准。“已实现”只表示机制、诊断或防护存在，不表示科学假设成立。

| ID | 状态 | 当前问题 | 下一步判据 |
|---|---|---|---|
| EXEC-01 | v0.25 结构完成 | manifest 绝对路径跨机器迁移可能破坏预注册信任链。 | 使用路径前缀映射并验证 progress、config、checkpoint SHA-256；任何 mismatch 停止。 |
| EXEC-02 | v0.25 结构完成 | 同 checkpoint 的重复分支浪费算力并增加中断概率。 | 仅按相同 checkpoint hash 与 intervention 合并最长轨迹；每个 anchor 仍按自己的 event/horizon 截断。 |
| EXEC-03 | v0.27 防护完成 | 旧 marker 不含共同边界或 cohort，静默复用会伪造诊断完整性。 | marker 绑定 diagnostic mode/schema；缺字段的旧 marker 必须重跑。 |
| SYNTH-01 | v0.27 结构完成 | 多批结果重复、覆盖不齐，人工拼表易产生伪重复和版本混用。 | 只按 immutable anchor/intervention 合并；核心世界结果冲突时拒绝，诊断更完整版本才可替代。 |
| SYNTH-02 | 开放 | 当前仅 72/108 eligible pairs；缺口集中在 mortality/scarcity 的 policy、memory、Top-k。 | 完成 signed remaining-event knowledge plan 后再比较知识层跨事件作用。 |
| SCALE-01 | 开放 | scarcity exposure 接近饱和，不能与 crowding/mortality z-score 横向比较。 | 始终按 event kind 分层；必要时升级 exposure 指标 schema，而非事后调阈值。 |
| REPLICATION-01 | 防护完成 | 同一 seed 内两个 anchors 不是独立重复。 | 先 seed 内平均，再跨 seed 报方向；三 seed 不作显著性结论。 |
| CAUSAL-01 | 开放，已有工具 | 自然事件 exposure 不是随机分配，paired branch 只识别 checkpoint 后机制效应。 | 结论限定于预注册 checkpoint/horizon，不声称事件暴露本身因果。 |
| CULTURE-01 | 跨事件机制近端复制 | transfer-off 后 active transferred roots 在 crowding、mortality、scarcity 的三个 seed 中均下降，均值分别 `-84.33/-50.50/-36.33`。 | 可解释为短 horizon 文化状态维持；不得称为人口、适应度或主体性收益。 |
| CULTURE-02 | 人口收益未建立 | commits 与 roots 是传播操作和文化状态，不是 demographic outcome。 | 使用 event cohort 组件与更长 horizon；不从 roots 下降推出生存代价。 |
| CULTURE-03 | 开放 | transfer-off 后 new/lost roots 不必为零，因为既有 transferred roots 可迁移、消失或进入区域。 | 以 future commits=0 作 manipulation check；root 指标只描述区域文化状态转移。 |
| GROUP-01 | 测量纠缠已识别 | freeze refresh 的 current-label cohesion 在三类事件中下降，但 common-boundary cohesion 无跨 seed 稳定方向。 | 优先 common-boundary 指标；current/common gap 解释为评价分区变化，不是社会机制本身。 |
| GROUP-02 | 开放 | 冻结刷新同时改变标签陈旧度、新生体吸纳与分支当前 grouped fraction。 | 结合共同边界、cohort、grouped fraction 和出生构成；必要时预注册固定周期对照。 |
| COHORT-01 | v0.27 诊断完成，结果待跑 | `final_alive_region` 混合留存、迁出、缺失、迁入和事件后出生。 | v4 results 必须报告五类 stable-ID endpoint component 且 balance residual=0。 |
| COHORT-02 | 开放 | v0.27 只有终点分解，不记录 horizon 内多次出入区域或死亡时点。 | 只有当终点组件仍无法区分机制时，才设计路径级 flow ledger；避免无目的日志膨胀。 |
| COHORT-03 | 防护完成 | 槽位复用可能让新生实体继承事件 cohort 身份。 | stable entity ID 而非 slot index 定义 cohort；测试覆盖死亡与槽位复用。 |
| AFFINITY-01 | 跨事件方向不稳 | neutralize affinity 的 region alive 在 crowding 为三 seed 正，mortality/scarcity 较弱或混合。 | 用 cohort 分解判断 crowding 方向来自留存、迁移还是出生，不调整 affinity 参数。 |
| MEMORY-01 | crowding 描述性方向 | ablate working memory 在 crowding 的 region alive 三 seed正、mortality 三 seed负，但仍是区域构成且只覆盖一种事件。 | cohort 复跑并复制到 mortality/scarcity；不得解释为记忆普遍有害。 |
| STRATEGY-01 | 覆盖未完成 | policy influence、working memory、Top-k 仅在 crowding 完成 paired branches。 | 完成 36 个 remaining pairs 后，按事件类别和机制层级解释。 |
| DANGER-01 | 当前不可识别 | flagship 配置 danger evidence disabled。 | 继续标记 neutralization ineligible；仅在独立预注册启用配置评价。 |
| TRACE-01 | 机制完成，解释开放 | mortality trace 是实体死亡形成的局部证据，观察相关不等于适应价值。 | 在启用 inherited evidence mixture 的 paired checkpoint 中评价，伤害公式不改。 |
| LINEAGE-01 | 开放 | 遗传世系、群组和文化状态可能共同受人口瓶颈驱动。 | 在相同 checkpoint 对齐 lineage、文化和 cohort 组件，不使用单一相关。 |
| TIME-01 | 开放 | 世界 tick 不等于演化世代，120-tick horizon 也不等于相同出生机会。 | 同时报告世代、出生量、有效谱系和事件 cohort 组成。 |
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
2. 自然事件 exposure 未随机化；paired branch 识别的是 checkpoint 后机制效应。
3. commits 与 roots 是机制近端指标，不等于人口、适应度或主体性。
4. current-label cohesion 对 group-refresh 干预存在定义耦合；共同边界结果显示原方向主要由分区改变产生。
5. event cohort 终点分解可拆人口构成，但仍不是完整路径流量或死亡时序。
6. 群组、谱系和知识候选图都不能单独证明主体存在或主体偏移。
7. 默认关闭环境插件、娱乐控制器和直接行动覆盖不得混入科学基线。
