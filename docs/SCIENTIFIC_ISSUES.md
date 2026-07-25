# 科学问题与研究债务

本文件以 v0.24 代码和三个 seed、1500 tick 的长期分析为准。状态“已实现”只表示机制或防护存在，不表示科学假设成立。

| ID | 状态 | 当前问题 | 下一步判据 |
|---|---|---|---|
| CAUSAL-01 | 开放，已有工具 | 原始相关、首差分、偏相关、cross-lag 和自然事件窗口仍可能受共享时间趋势、空间选择和事件选择影响。 | 使用 v0.24 manifest，从相同事件前 checkpoint 执行 baseline/ablation；结论限定于预注册 horizon。 |
| EVENT-01 | v0.24 结构修正完成 | 旧局部事件选择会参考 cohesion validity，且单 run、单 event kind 规划不利于预注册矩阵。 | 新矩阵必须保持 `exposure-only-local-peak-selection-v1`，分析摘要不得参与锚点选择，计划哈希必须在执行前固定。 |
| CULTURE-01 | 因果开放 | 三 seed 均有 12k–14k committed transfers 和约 2k effective transferred roots，证明传播存在；不证明传播提高人口、遗传多样性或适应度。 | 在 scarcity/crowding/mortality anchor 上比较 transfer-off 与 baseline 的根建立、留存、跨区域扩散和局部人口。 |
| CULTURE-02 | 开放 | 稀缺同时与“新根出现”正相关、与“净根建立”负相关，可能表示高周转而非文化适应。 | 分离新增、丢失、活跃、跨区域和多区域 roots；报告短期与较长 horizon 的方向是否一致。 |
| GROUP-01 | 候选主体，因果开放 | 群组由高信任关系和阈值规则识别。三个 run 仅刷新 15 次、跳过 1485 次；群组标签可能既是社会结构测量，也是后续方向输入。 | 使用 `freeze-group-refresh`，比较相同 checkpoint 下标签更新、群组边界流和文化传播变化；不得把 NMI 或 cohesion 单独解释为主体存在。 |
| GROUP-02 | 开放 | 冻结刷新后，死亡成员清除、新生体未分组，故干预同时改变标签陈旧度和新成员吸纳。 | 报告 horizon 内出生/死亡量与 grouped fraction；需要时另行预注册“固定周期”对照，不在本干预中混合。 |
| LINEAGE-01 | 开放 | 有效遗传世系与 cohesion 在三个 seed 中稳定负相关，但最大世系占比的偏相关方向不一致。 | 使用相同生态事件的 paired branches，区分人口瓶颈、群组边界和知识传播对谱系集中度的短期影响。 |
| STRATEGY-01 | 开放 | 策略有效维度与动作熵高度同步，可能含共同时间趋势；固定 8-action × 16-feature 架构限制可演化空间。 | 报告首差分和 checkpoint 消融；架构扩展必须作为新 schema，而非静默改变旧基因语义。 |
| TIME-01 | 开放 | 世界 tick 不等于演化世代。1500 tick 的谱系变化不能直接称为长期进化均衡。 | 同时报告世代深度、出生量、有效谱系和选择后果；跨配置比较按世代与事件数对齐。 |
| AFFINITY-01 | 因果开放 | 四资源亲和是固定预算表型，已被环境使用，但尚未证明提高长期多样性。 | 在自然事件锚点执行 `neutralize-resource-affinity`；比较资源 channel、行为和繁殖后果。 |
| DANGER-01 | 当前输入不可识别 | 本次旗舰配置的 danger evidence schema 为 disabled，direct/trace 权重恒为 1。 | manifest 必须将 `neutralize-danger-evidence` 标记 ineligible；只有启用 inherited mixture 的预注册配置才能评价。 |
| TRACE-01 | 机制完成，解释开放 | mortality trace 是实体死亡形成的局部环境证据。死亡与凝聚度的观察方向不等于死亡痕迹有适应价值。 | 在启用 evidence mixture 的 paired checkpoint 中比较 neutralization；实际伤害公式保持不变。 |
| ENV-01 | 边界完成 | 生物型危险源会复制现有实体语义并混淆主体层级。 | 科学核心不新增第二套生命周期；合成移动场仅作为默认关闭插件，启用时不得标为科学生态基线。 |
| ENV-02 | 开放 | 当前信息语义仍固定为资源、危险、社会三类通道；新增环境证据需要绑定已有 danger 词汇。 | 设计版本化任意信息通道 schema，保持旧配置与 checkpoint 不变。 |
| SUBJECT-01 | 开放 | 身体、谱系、社会和知识节点都是候选主体结构，不是主体性定论。 | 需要跨尺度维持、边界修复、控制贡献和反事实删除的多指标矩阵，并保留否定结果。 |
| SHIFT-01 | 开放 | 主体偏移不能写成实体状态或由单次社会依赖代理推出。 | 预注册事件窗口和 matched non-events；比较控制来源、物质流和删除干预，不使用人工“恢复”变量作为科学证据。 |
| GPU-01 | 未完成 | `hybrid-accelerated` 多 tick parity 尚未证明；设备浮点和提交顺序可能改变离散后果。 | 在真实 CUDA 上逐阶段定位首差异，并对完整 checkpoint/日志做长程对照。科学运行继续使用 strict-reference。 |
| CHECKPOINT-01 | 已有防护 | `.sechk` 包含 pickle，无法安全加载不可信来源。 | 只加载本项目可信输出；未来如需交换，设计非可执行、版本化状态格式。 |
| REPRO-01 | 部分完成 | stateless random 容量仲裁消除了稳定 ID 优先，但失败尝试成本和同 tick 槽位释放仍是模型选择。 | 分别作为新规则 schema 预注册，不能因“更真实”直接修改默认语义。 |
| GENOME-01 | 开放 | 固定形态槽、初代分布、突变率和网络宽度仍约束可达演化空间。 | 做 schema-level sensitivity matrix；不把某一组超参数下的稳定性当作普遍规律。 |

## 当前解释边界

1. 跨 seed 同号支持稳健方向，不支持必要性。
2. 自然事件锚点不是随机暴露；paired branch 只识别在该 checkpoint 后关闭某机制的短期效应。
3. 传播量、文化根数量和跨谱系传播不等于适应性文化演化。
4. 群组、谱系和知识候选图都不能单独证明主体存在或主体偏移。
5. 默认关闭的环境插件、娱乐控制器和直接行动覆盖不得混入科学基线。
