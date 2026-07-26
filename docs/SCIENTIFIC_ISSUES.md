# 科学问题与研究债务

本文件以 v0.26 代码、三个 seed 的 1500-tick 长跑、18-anchor manifest 和已完成的 crowding 配对结果为准。“已实现”只表示机制或防护存在，不表示科学假设成立。

| ID | 状态 | 当前问题 | 下一步判据 |
|---|---|---|---|
| EXEC-01 | v0.25 结构完成 | manifest 绝对路径跨机器迁移可能破坏预注册信任链。 | 使用路径前缀映射并验证 progress、config、checkpoint SHA-256；任何 mismatch 停止。 |
| EXEC-02 | v0.25 结构完成 | 同 checkpoint 的重复分支浪费算力并增加中断概率。 | 仅按相同 checkpoint hash 与 intervention 合并最长轨迹；anchor summary 按独立 event/horizon 截断。 |
| EXEC-03 | v0.26 防护完成 | 旧 trajectory 不含共同边界字段，若静默复用会制造虚假“共同口径”。 | marker 必须绑定 common-boundary mode 与 schema；v1 marker 不作为 v2 common-boundary trajectory 复用。 |
| SCALE-01 | 开放 | scarcity exposure 接近饱和，锚点 z-score 约 0.55–0.60；crowding/mortality 约 3.3–3.9。 | 按 event kind 分层；不跨类型按 z-score 排名。 |
| REPLICATION-01 | 防护完成 | 同一 seed 内多个 anchors 不独立。 | 先 seed 内平均，再跨 seed 报方向；三 seed 不作显著性结论。 |
| CAUSAL-01 | 开放，已有工具 | 自然事件暴露不是随机分配，paired branch 只关闭后续机制。 | 结论限定于预注册 checkpoint/horizon；不得声称事件暴露本身因果。 |
| EVENT-01 | v0.24 结构完成 | 事件锚点若读取 outcome 会产生选择泄漏。 | 保持 exposure-only selection；analysis 仅作 rationale/audit。 |
| RESULT-01 | v0.26 结构完成 | transfer commits、文化根、cohesion、alive 的因果距离不同，混在一表易产生过度解释。 | outcome audit 将其分类为 manipulation、mechanism-proximal、boundary metric、downstream region state。 |
| CULTURE-01 | 机制近端方向已支持 | crowding anchors 中关闭传播后 active transferred roots 三 seed 均下降，均值 `-84.33`。 | 复制到 scarcity/mortality；该方向只说明局部文化状态维持，不等于适应性。 |
| CULTURE-02 | 人口收益未建立 | transfer-off 的区域 alive 为 2 seed 正、1 seed 负；cohesion 方向也不一致。 | 使用更多 event kinds、固定 cohort 与更长 horizon；不从文化根下降推出人口代价。 |
| CULTURE-03 | 开放 | transfer-off 后 region new roots 不为零，因为既有 transferred roots 可在新窗口进入/离开区域。 | 将“未来 commit=0”作为操作检验；new/lost root 解释为区域状态转移，不误称新传播。 |
| GROUP-01 | v0.26 测量修正完成，因果开放 | `freeze-group-refresh` 与 current-label cohesion 共用被干预标签，原三 seed 同向下降 `-0.2103` 存在测量耦合。 | 运行 common-boundary rerun，以 `post_event_reference_cohesion_region` 为首选结果。 |
| GROUP-02 | 开放 | 冻结刷新同时改变标签陈旧度与新生体吸纳；死亡成员仍清除。 | 报告 grouped fraction、出生死亡与共同边界 gap；必要时预注册固定周期对照。 |
| GROUP-03 | v0.26 防护完成 | 槽位复用可能让新生实体错误继承 checkpoint 群组。 | common boundary 同时匹配 slot 与 stable entity ID；不匹配者视为边界外。 |
| POP-01 | 开放 | `final_alive_region` 混合存活、出生、死亡和迁移。affinity neutralization 的三 seed `+7.33` 不能直接称为生存优势或代价。 | 新增 checkpoint-fixed cohort survival、retention 与 migration outcomes，再讨论 demographic effect。 |
| AFFINITY-01 | 复制优先 | crowding 下 neutralize-resource-affinity 的 region alive 三 seed 同向增加。 | 复制到 scarcity/mortality；结合 cohort 与资源 channel 结果判断是迁移、瓶颈缓解还是适应成本。 |
| DANGER-01 | 当前输入不可识别 | flagship 配置 danger evidence disabled，direct/trace 权重恒为 1。 | 继续标记 `neutralize-danger-evidence` ineligible；仅在独立预注册启用配置评价。 |
| TRACE-01 | 机制完成，解释开放 | mortality trace 是实体死亡形成的局部证据，观察相关不等于适应价值。 | 在启用 inherited evidence mixture 的 paired checkpoint 中 neutralize；伤害公式不改。 |
| LINEAGE-01 | 开放 | 遗传世系与群组/文化状态可能共同受人口瓶颈驱动。 | 在相同事件 checkpoint 比较 lineage、knowledge roots 和人口后果，不使用单一相关。 |
| STRATEGY-01 | 开放 | 固定 8-action × 16-feature 与量化知识路由限制可演化空间。 | 补齐 knowledge-policy、memory、Top-k crowding 消融；架构扩展使用新 schema。 |
| TIME-01 | 开放 | 世界 tick 不等于演化世代。 | 同时报告世代、出生量、有效谱系与事件数；跨配置按世代/事件对齐。 |
| ENV-01 | 边界完成 | 生物型危险源会复制现有实体语义并混淆主体层级。 | 科学核心不新增第二套生命周期；合成移动场只作默认关闭插件。 |
| ENV-02 | 开放 | 信息通道仍固定为资源、危险、社会。 | 设计版本化任意信息通道 schema，保持旧配置/checkpoint 兼容。 |
| SUBJECT-01 | 开放 | 身体、谱系、社会和知识节点都是候选主体结构，不是主体性定论。 | 需要维持、边界修复、控制贡献和删除反事实多指标矩阵。 |
| SHIFT-01 | 开放 | 主体偏移不能写成实体状态或由单次依赖代理推出。 | 预注册 matched non-events 与跨尺度控制/物质流比较。 |
| GPU-01 | 未完成 | `hybrid-accelerated` 多 tick parity 尚未证明。 | 真实 CUDA 逐阶段定位首差异；科学运行继续 strict-reference。 |
| CHECKPOINT-01 | 已有防护 | `.sechk` 包含 pickle，无法安全加载不可信来源。 | 只加载本项目可信输出；未来设计非可执行交换格式。 |
| REPRO-01 | 部分完成 | stateless capacity arbitration 修复 ID 偏差，但失败成本与同 tick 槽位释放仍是模型选择。 | 作为独立规则 schema 预注册，不静默修改。 |
| GENOME-01 | 开放 | 初代分布、突变率、固定形态槽和网络宽度约束可达空间。 | 做 schema-level sensitivity matrix，不把单组超参数稳定性当普遍规律。 |

## 当前解释边界

1. 三 seed 同号是描述性稳健方向，不是统计必要性。
2. 自然事件 exposure 未随机化；paired branch 识别的是 checkpoint 后机制效应。
3. commits 与 roots 是机制近端指标，不等于人口、适应度或主体性。
4. current-label cohesion 对 group-refresh 干预存在定义耦合；必须使用共同边界复跑。
5. 区域人口不是固定 cohort，迁移可改变方向。
6. 群组、谱系和知识候选图都不能单独证明主体存在或主体偏移。
7. 默认关闭环境插件、娱乐控制器和直接行动覆盖不得混入科学基线。
