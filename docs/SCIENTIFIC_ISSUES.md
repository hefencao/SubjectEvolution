# 科学问题与研究债务

## v0.37 D1-B resource-demand questions

| ID | 状态 | 科学价值与当前问题 | 后续执行条件 |
|---|---|---|---|
| ENV-D0-04 | 已触发停止条件 | 上传的三 seed 结果中，全局资源有效维度降至 1.265–1.309，通道平均绝对相关升至 0.812–0.834；外生场正交性被统一四通道采集重新压成共同稀缺轴。 | 先验证选择性采集能否跨 seed 保持资源/需求维度，再继续 D2。 |
| DEMAND-D1B-01 | 机制完成，长程未决 | `affinity-sampled-exclusive-harvest-v1` 由遗传亲和采样单一通道，总请求预算固定；短程显示需求解耦，但人口和提取效率下降。 | 报告资源维度、需求维度、提取效率、人口与谱系；不得只挑“维度提高”作为成功。 |
| DEMAND-D1B-02 | 已有防护 | 选择性采集使用 state-free keyed randomness，不读取局部丰度；避免所有实体同步追逐同一局部最丰富通道。 | CPU/GPU planner parity、stable-ID key 和固定预算测试持续保留。 |
| DEMAND-D1B-03 | 开放 | 单通道请求可能因局部不足产生空采，机会成本可能过强，导致生态轴存在但总体种群不可持续。 | 三 seed 检查 extraction efficiency、alive、birth/death 和资源限制；必要时预注册混合预算 schema，不事后调比例。 |
| DEMAND-D1B-04 | 开放 | 资源亲和既影响感知/同化，也影响采集通道概率，可能把多个机制效应捆绑。 | 使用共同 checkpoint `neutralize-resource-affinity`，并区分需求路由、同化效率和策略观察贡献。 |
| ANALYSIS-D1-01 | 已修复契约 | 用户提供的 aggregate 是 v10，遗漏容量字段；旧分析器会让 D1 长跑看似完整但无法评价容量。 | v12 发布 analyzer/runtime version；D1 resolved config 缺少 `capacity_*` 时拒绝分析。 |
| DIFF-D1-01 | D1-A 机制完成，经验未决 | 四类容量真实限制工作记忆、知识、关系和注意力，但上传 aggregate 无容量字段，长期选择响应仍未知。 | 用 v0.37 重新分析新长跑，并做容量表达中和。 |
| DIFF-D1-02 | 开放 | 四类容量可能收敛为单一总体复杂度轴，而非独立生态性状。 | 报容量 covariance/effective dimensions、利用率、饱和率及环境相位条件性。 |
| DIFF-D2-01 | 阻塞 | 通用表达模块若在资源需求和容量机制尚未识别时加入，会扩大不可归因空间。 | D1-B 至少两个 seed 保持非平凡环境/需求维度，并有 matched neutralization 证据后再启动。 |

## v0.32 架构与性能债务

| ID | 状态 | 当前问题 | 下一步判据 |
|---|---|---|---|
| ARCH-01 | 部分完成 | `Simulation.step()` 仍约 1200 行，依赖大量共享局部变量；简单剪贴会隐藏提交顺序。 | 先定义 `StepContext`、phase plan/result 和只读/写边界，再拆 observation、control、resolution、commit、lifecycle。 |
| ARCH-02 | 部分完成 | `runtime/reporting.py` 仍约 1800 行，manifest、scientific validity、progress 和 metrics 发布协议仍耦合。 | 按独立版本化 publisher 拆分，保持输出字段、排序和旧 schema 一致。 |
| ARCH-03 | 开放 | `config.py` 同时承担 dataclass、解析、验证、默认迁移和 schema 兼容。 | 在新增 D1/D2 schema 前拆成 definitions/parser/validation/migrations，并增加旧配置 round-trip。 |
| PERF-01 | 已定位 | policy contribution 逐项构造字典并逐行写 CSV，是当前 120-tick CPU 基准最大热点和约 25 MB 输出来源。 | 先增加可审计 sampling/aggregation 与批量 writer；完整日志模式必须保持字段和顺序兼容。 |
| PERF-02 | 已定位 | knowledge outcome、latent hash/projection 和稀疏路由仍含大量 Python 循环与小数组操作。 | 用 phase profiling 证明占比，再迁入固定布局 NumPy/CuPy kernel；逐阶段与 CPU reference parity。 |
| PERF-03 | 边界清晰 | strict-reference 科学运行仍以 CPU 世界为权威；hybrid 路径不是完整设备驻留。 | 真实 CUDA 环境建立多 tick stage parity、host/device transfer 和 kernel profile，不能以设备可用替代加速证明。 |
| NATIVE-01 | 暂缓整体迁移 | 直接将世界重写为 C++/Rust 会复制规则、checkpoint 和实验协议，增加双实现漂移。 | 仅当稳定 phase 占目标长跑至少约 20%，且 Python/CuPy 优化不足并已有 plan/result API 与 parity 时，引入原生 kernel。 |
| SHADER-01 | 非权威候选 | graphics/WebGPU compute shader 的浮点、驱动和编译器验证矩阵不适合作为当前科学权威世界。 | 只用于 renderer 同进程预览、热图或近似交互；不得产生 scientific checkpoint 或与 reference result 混合。 |

## v0.31 分化主线新增问题

| ID | 状态 | 科学价值与当前问题 | 后续执行条件 |
|---|---|---|---|
| ENV-D0-01 | 外生结构完成、实现需求曾坍缩 | 四资源外生生成可保持高维，但 D1-A 三 seed 中统一采集把实现资源维度压回约 1.27–1.31。 | 用 D1-B 检验 phenotype-routed demand 是否跨 seed 保持环境轴。 |
| ENV-D0-02 | 开放 | `resource_effect_matrix` 仍是设计者定义的固定身体接口，矩阵尺度可能让某些通道几乎不限制适应度。 | 做通道中和、交换、缩放和限制因子审计；区分环境方差与选择强度。 |
| ENV-D0-03 | 开放 | 四个周期和波向量来自预注册配置，可能对地图尺寸、边界和采样尺度敏感。 | 至少比较一套独立参数、地图尺度和 atlas 分区；不在结果后调参。 |
| DIFF-D1-01 | D1-A 机制完成，分析需重跑 | 工作记忆、知识、关系和知识注意力容量已独立遗传；用户 aggregate 由 v10 生成并遗漏容量字段。 | 以 v0.37 v12 分析器运行 D1-B 长程和表达中和，再评价容量选择。 |
| DIFF-D2-01 | 阻塞 | 通用表达模块必须与现有 latent router 区分，否则只是重复策略网络；D1-B 长程尚未完成。 | 只有资源/需求维度和容量条件性结果通过后，才连接具身物理端口并增加同源/消融证据。 |

本文件以 v0.37 代码、既有三个 seed 的 1500-tick D0 前置长跑、18-anchor manifest、108/108 event-timed pairs，以及 D1-A 容量机制与短程配对 smoke 为准。“已实现”只表示机制、诊断或防护存在，不表示科学假设成立。

| ID | 状态 | 当前问题 | 下一步判据 |
|---|---|---|---|
| EXEC-01 | 结构完成 | manifest 跨机器迁移可能破坏预注册信任链。 | 路径映射后验证 progress、config、checkpoint、plan SHA-256；任何 mismatch 停止。 |
| EXEC-02 | v0.28 完成 | prior-checkpoint 与 event-timed 是不同估计量。 | 结果必须携带 intervention timing；综合器拒绝混合。 |
| EXEC-03 | v0.28 完成 | 人数相同不能证明 event cohort 身份相同。 | event alive、global stable-ID hash、regional stable-ID hash 全部一致；本轮 108/108 pairs 通过。 |
| SYNTH-01 | v0.29 覆盖完成 | 多批结果重复或覆盖不齐会产生伪重复。 | 只按 immutable anchor/intervention 合并，核心结果冲突即拒绝；本轮 coverage=108/108。 |
| REPLICATION-01 | 防护完成 | 同一 seed 内两个 anchors 不是独立重复。 | 先 seed 内平均，再跨 seed 报方向；三个 seed 不作显著性结论。 |
| CAUSAL-01 | 开放，边界清晰 | 自然事件 exposure 未随机分配。 | event-timed branch 只识别共同自然事件状态后的短期机制效应，不声称 exposure 本身因果。 |
| CULTURE-01 | 跨事件机制近端复制 | event-timed transfer-off 在三类事件中均减少 active transferred roots 和传播活动。 | 可称“短期局部文化状态维持”；不得升级为人口、适应度或主体性收益。 |
| CULTURE-02 | 人口收益未建立 | commits 与 roots 是传播操作/文化状态，不是 demographic outcome。 | 只在共同 cohort 上解释 retained、absent、migration、birth；跨事件人口方向仍需一致。 |
| MEMORY-01 | 情境依赖 | working-memory ablation 增加 outgoing commits 的方向跨事件出现，但下游人口与文化方向不统一。 | 做机制链分层：policy residual→action opportunity→commit→root→cohort；不据 commits 调参。 |
| STRATEGY-01 | 情境依赖 | policy、memory、Top-k 的方向随 crowding/mortality/scarcity 改变。 | 维持当前默认机制；增加预注册事件类型×机制矩阵与长期 outcome，不进行事后参数选择。 |
| GROUP-01 | v0.29 协议显式化 | 当前 label 是阈值化有向边上的固定轮最小标签传播，不是精确连通分量。 | rounds、threshold、minimum members 必须进入 schema/provenance；做敏感性矩阵。 |
| GROUP-02 | 测量纠缠已识别 | freeze refresh 会直接改变 current-label cohesion 的评价分区。 | 优先 checkpoint-common cohesion；current/common gap 只解释边界定义。 |
| GROUP-03 | 开放 | 有向 trust 边、8 轮传播和 stable-root token 可能对网络直径、槽位布局与阈值敏感。 | 比较传播轮数、对称化边和精确弱连通组件的**离线诊断**，不得静默替换基线 schema。 |
| GROUP-04 | 开放 | adaptive refresh 的最短/最长周期会改变标签陈旧度与新生体吸纳。 | 在相同世界轨迹离线重放 refresh schedules；若反馈世界则作为独立预注册规则版本。 |
| REGION-01 | v0.29 协议显式化 | 固定 4×4 归一化分区在更大地图上代表更大物理面积。 | 报告 physical width/height、world cells/region 与 partition hash；不同几何默认不池化。 |
| REGION-02 | 开放 | 改变世界网格分辨率会改变每区 world-cell 数和局部场平滑尺度。 | 预注册 fixed-count、fixed-physical-size 或 fixed-cell-count 三种独立 schema，不能自动宣称尺度不变。 |
| REGION-03 | 开放 | 周期世界上边界附近的单一区域统计没有显式 wrap-aware 邻域合并。 | 若研究跨边界空间事件，增加独立 toroidal neighborhood schema；不修改现有 row-major region identity。 |
| ANCHOR-01 | v0.29 v2 | anchor 由区域自身 80% 分位以上的内部局部峰和区域内 z-score 排序确定。 | 候选规则、排名、区域多样性、checkpoint 与 partition hash 全部发布。 |
| ANCHOR-02 | 开放 | z-score 仅在区域自身时间序列内标准化，不可跨事件类型或不同 partition geometry 比较。 | 按 event kind 和 partition hash 分层；禁止用 z-score 声称统一压力强度。 |
| ANCHOR-03 | 开放 | scarcity 指标接近饱和，局部 z-score 小且事件解释弱于 crowding/mortality。 | 先做 exposure schema 校准与敏感性分析，不事后调 quantile 追求更强结果。 |
| ANCHOR-04 | 开放 | “优先不同区域”增加空间覆盖，但不是概率抽样，可能偏向少量强峰区域。 | 发布所有 candidate ranks；比较 distinct-region 与 unrestricted top-k 作为预注册选择方案。 |
| COHORT-01 | v0.28 完成 | endpoint decomposition 不是完整路径级 birth/death/migration ledger。 | 只有 endpoint 仍无法解释机制时才增加路径日志。 |
| COHORT-02 | 防护完成 | 槽位复用可能让新实体继承 cohort 身份。 | stable entity ID 而非 slot 定义 cohort；测试覆盖槽位复用。 |
| AFFINITY-01 | 情境依赖 | resource-affinity neutralization 对人口、死亡和文化指标缺少跨事件统一方向。 | 不修改亲和预算；先做地图/区域尺度敏感性与 cohort 机制链。 |
| DANGER-01 | 当前不可识别 | flagship 配置 danger evidence disabled。 | 继续标记 neutralization ineligible；仅在独立预注册启用配置评价。 |
| TRACE-01 | 机制完成，解释开放 | mortality trace 是实体死亡形成的局部证据，观察相关不等于适应价值。 | 在 inherited evidence mixture 启用的 event-timed paired 配置中评价。 |
| LINEAGE-01 | 开放 | 遗传世系、群组和文化状态可能共同受人口瓶颈驱动。 | 在相同 event checkpoint 对齐 lineage、文化和 cohort 组件。 |
| TIME-01 | 开放 | 世界 tick 不等于演化世代，120-tick horizon 不等于相同出生机会。 | 同时报告世代、出生量、有效谱系和共同 cohort 组成。 |
| ENV-01 | 边界完成 | 生物型危险源会复制现有实体语义并混淆主体层级。 | 科学核心不新增第二套生命周期；合成移动场只作默认关闭插件。 |
| ENV-02 | 开放 | 信息通道仍固定为资源、危险、社会。 | 设计版本化任意信息通道 schema，保持旧配置/checkpoint 兼容。 |
| SUBJECT-STRUCT-01 | v0.30 测量完成 | 当前候选社会结构此前只有截面节点和累计 benefit，缺少跨 refresh 的连续性。 | 使用 stable-ID membership succession 报 formation/dissolution/split/merge/Jaccard；不得把 overlap edge 当成主体身份定理。 |
| SUBJECT-STRUCT-02 | 开放 | 同一 group token 可能在成员大幅更替后仍存续，token 改变也可能保留大部分成员。 | 同时报告 same-token、exact-membership、Jaccard、source retention 和 target inheritance；不使用单一 token 判定连续性。 |
| SUBJECT-STRUCT-03 | 开放 | 当前只有 body、lineage、single-level social group，尚无 group-of-groups、制度或任意嵌套。 | 先定义版本化层级/包含/控制/维护边，再实现可回放嵌套图；不得把 succession tracker 冒充嵌套数据库。 |
| SUBJECT-ENV-01 | v0.30 测量完成、因果开放 | 谱系或社会群组的实现环境暴露可能不同，但 association 同时受迁移、共同历史、人口瓶颈和标签粒度影响。 | 报 covered fraction、scale、span 和共同时间趋势；后续使用 matched environment-phase interventions。 |
| SUBJECT-ENV-02 | 开放 | 多尺度 association 可能随 region count 机械变化，粗尺度平均差异、细尺度放大局部迁移。 | 预注册 2×2/4×4/8×8，不事后挑尺度；只有跨尺度/跨 seed 稳定方向才进入反事实阶段。 |
| ENV-ATLAS-01 | v0.30 测量完成 | 六维 signature 仍由固定四资源、hazard、mortality trace 构成，不等于任意环境空间。 | 报 schema 和维度；新增环境维度必须新 schema 并保持旧 checkpoint/分析兼容。 |
| ENV-ATLAS-02 | 开放 | Euclidean signature distance 与 covariance effective dimensions 受各维量尺和饱和影响。 | 保持容量归一化，报告各维分布；比较 robust scaling 只能作为新诊断 schema。 |
| SUBJECT-01 | 开放 | 身体、谱系、社会和知识节点都是候选主体结构，不是主体性结论。 | 需要维持、边界修复、控制贡献和删除反事实多指标矩阵。 |
| SHIFT-01 | 开放 | 主体偏移不能写成实体状态或由单次依赖代理推出。 | 预注册 matched non-events 与跨尺度控制/物质流比较。 |
| GPU-01 | 未完成 | `hybrid-accelerated` 多 tick parity 尚未证明；当前科学运行是 strict-reference。 | 真实 CUDA 逐阶段定位首差异；科学运行继续 strict-reference。 |
| CHECKPOINT-01 | 已有防护 | `.sechk` 含 pickle，无法安全加载不可信来源。 | 只加载本项目可信输出；未来设计非可执行交换格式。 |
| REPRO-01 | 部分完成 | stateless capacity arbitration 修复 ID 偏差，但失败成本与同 tick 槽位释放仍是模型选择。 | 作为独立规则 schema 预注册，不静默修改。 |
| GENOME-01 | 开放 | 初代分布、突变率、固定形态槽和网络宽度约束可达空间。 | 做 schema-level sensitivity matrix，不把单组超参数稳定性当普遍规律。 |

## 当前解释边界

1. 三 seed 同号是描述性复制，不是统计必要性。
2. 自然事件 exposure 未随机化；event-timed paired branch 也不识别 exposure 本身因果。
3. commits 与 roots 是机制近端指标，不等于人口、适应度或主体性。
4. current-label cohesion 对 group-refresh 干预存在定义耦合，应优先共同边界。
5. group label 是有向、有限轮次候选分组，不是精确无向组件或主体存在判定。
6. 固定归一化区域数不代表固定物理尺度；不同 partition hash 默认不池化。
7. anchor z-score 是区域内排序量，不是跨事件、跨地图的统一压力尺度。
8. event cohort 只有在 stable-ID identity hashes 相同时才是共同 cohort。
9. endpoint cohort 分解不是完整路径流量或死亡时序。
10. succession overlap 是候选结构的成员连续性，不是主体身份、繁殖或制度继承。
11. environment association 是实现暴露分化，不识别环境选择方向或主体主动适应。
12. atlas scale、covered fraction 和 label size 必须共同报告，禁止事后选择最强尺度。