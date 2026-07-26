# Changelog

## 0.37.0

### D1-B phenotype-routed resource demand

- Added `affinity-sampled-exclusive-harvest-v1`: each HARVEST action spends the historical total request budget on one channel sampled from inherited resource affinity.
- Added a state-free keyed harvest-channel random stream shared by CPU and GPU planners.
- Left unselected channels at zero and did not reassign locally unavailable budget, creating an explicit extraction-efficiency cost.
- Corrected partial-harvest outcome classification for exclusive requests.
- Added D1-B smoke and 1500-tick long-run configs.
- Upgraded protocol audit to v5 and long-run analysis to v12.
- Added analyzer/runtime provenance, strict D1 field validation, capacity-use diagnostics, realized demand dimensions/correlations and extraction efficiency.

### Evidence boundary

- The uploaded v10 aggregate omitted D1 capacity fields and therefore cannot support capacity-selection conclusions.
- Its three seeds showed final resource dimensions of 1.265–1.309 with channel correlations of 0.812–0.834, triggering the D0 common-demand stop condition.
- A 300-tick same-seed smoke improved resource and demand dimensions but reduced extraction efficiency and population; no adaptive claim is made.

## 0.36.0

### D1-A inherited elastic capacities

- Added `inherited-elastic-capacities-v1` with four independent inherited effective capacities: working-memory dimensions, knowledge bytes, relationship slots and incoming knowledge-attention slots.
- Kept fixed physical array maxima and appended four capacity genes after all existing genome regions.
- Enforced per-entity masks in working memory, knowledge storage, social relations and transfer attention.
- Added per-tick structural maintenance and birth development energy costs while retaining existing use costs.
- Added capacity diagnostics, provenance, long-run trends/correlations, protocol audit v4 and long-run analysis v11.
- Added `neutralize-elastic-capacities`, which fixes midpoint expression without editing genotype and persists for future offspring and checkpoints.
- Added D1 smoke and 1500-tick multi-seed configurations.

### Validation

- Full suite: 167 passed, 1 real-CUDA test skipped before final packaging rerun.
- D1-disabled v0.35 comparison: 1268 common non-timing metric cells, selected logs and common authoritative state are unchanged.
- D1 paired tick-30→60 smoke verified immediate mechanism reach; no adaptive or ecological conclusion is claimed.

## v0.35.0

- 包导入根从 `subject_evolution` 改为 `se`。
- 移除 `domains` 与 `interfaces` 两层无信息目录；环境、GUI 和命令分别使用 `se.env`、`se.gui`、`se.cmd`。
- 高频文件使用 `cfg.py` 和 `runtime/sim.py`；其余易歧义领域名保留全称。
- console scripts 改为 `se`、`se-multi`、`se-gui`，不提供旧别名。
- 删除历史 checkpoint import bridge；旧 namespace checkpoint 采用重跑策略。
- 当前源码包不重复携带旧版本详细报告。


## 0.34.0

### Canonical imports

- 删除 35 个顶层 compatibility facade、通用 `_compat.py`、旧 `cli.py`、`multi_seed.py` 和 `gui_interface` package。
- 批量迁移 source、tests、scripts 和当前文档到 `runtime`、`domains`、`analysis`、`experiments`、`commands`、`interfaces` 规范路径。
- 只保留 `se.simulation` 作为历史 trusted-checkpoint pickle module bridge；不再支持通过旧模块 monkey-patch 规范实现。
- 将环境多样性原语移动到 `domains.environment.diversity`，消除 domain 对 analysis 的反向依赖。
- knowledge 子模块改为直接包内导入。

### Configs and scripts

- 69 个 JSON configs 批量加载和 schema 校验通过；配置为纯数据，不含需迁移的 Python module path，因此保持科学内容不变。
- 5 个 shell scripts 批量改用 `python -m se` 或 `python -m se.analysis.parity`。


## 0.33.0

### Entrypoints and compatibility facades

- 将规范单次运行和 multi-seed 命令迁入 `se.cmd`。
- `cli.py`、`multi_seed.py`、`simulation.py` 与 35 个历史模块进一步缩为薄 facade。
- 新增统一 `_compat.install_facade()`，保留旧 import、module execution、trusted checkpoint identity 和 monkey-patch 语义。
- 新增 `subject-evolution-multi-seed` console script；`subject-evolution` 直接指向规范 command implementation。

### Native GUI interface

- 将用户提供的 triple-buffer mmap bridge 整合到 `se.gui`。
- 保留 `se.gui_interface`、`eco_shm_bridge.py` 和 `run_simulation.py` 兼容路径。
- 新增原子 sidecar manifest、reference reader、稳定帧 double-check、attachment context manager、重复挂载防护和 checkpoint-aware GUI runner。
- 新增 `subject-evolution-gui` console script。
- GUI 明确为 Python-authoritative、one-way、observation-only 接口。

### Compatibility

- v0.32→v0.33 30-tick 非计时 metrics、核心日志、环境输出和完整权威状态零差异。
- v0.32 tick-15 checkpoint 可由 v0.33 精确续跑到 tick 30。
- GUI attached 与无 GUI 条件的权威状态和非计时输出一致。
- 全量测试 161 passed、1 skipped。

## 0.32.0

### Runtime and package refactor

- 将 5034 行 `simulation.py` 拆分为 `runtime/state.py`、`runtime/simulation.py`、`runtime/checkpointing.py`、`runtime/experiments.py` 和 `runtime/reporting.py`。
- 将 3118 行 `knowledge.py` 拆分为 types、storage、system、logging、diagnostics 以及 policy/latent/working-memory/routing 子模块。
- 将环境、演化、主体、知识、分析/审计和自然事件实验移动到分层 package。
- 历史顶层模块继续作为兼容 facade，保留旧导入、CLI、trusted checkpoint 和 monkey-patch 语义。
- 项目立项文档稳定命名为 `docs/PROJECT_CHARTER.md`。

### Performance baseline

- 缓存 CuPy 可用性检测，消除低层数组路径中重复 optional-import discovery。
- 共同 120-tick CPU 基准的三次 wall-time 中位数从 9.02 秒降至 7.10 秒。
- cProfile 总时间从 17.597 秒降至 11.794 秒；当前首要热点是 knowledge contribution 日志、CSV 写入、outcome 更新和 latent 路由。
- 明确迁移路线：Python reference/orchestration 保留；先优化日志与批处理，再以 CuPy custom kernels/C++ CUDA 迁移已证明热点；compute shader 只用于非权威预览。

### Compatibility

- 不改变世界规则、默认配置、随机键、提交顺序或日志字段。
- 新增 package architecture、facade identity、charter path 和 CuPy import cache 测试。
- v0.31→v0.32 默认世界、日志与 trusted checkpoint 兼容结果见 `docs/v0.32/`。

## 0.31.0

### D0 orthogonal environment

- 新增 `orthogonal-four-resource-niche-v1`，为四个既有资源通道配置独立空间主/次波、时间周期、相位、振幅和扩散率。
- 新增 D0 smoke 与 1500-tick long-run 配置；作用矩阵将资源连接到不同生命用途，但不预设生态角色。
- 环境场不读取实体、谱系、群组、策略或死亡反馈，不自动保护多样性。

### Audits and diagnostics

- 新增 `resource-environment-diversity-audit-v1`，报告空间/时间有效维度和通道相关矩阵。
- environment atlas 升级为 `multiscale-subject-environment-atlas-v2`，增加资源自身 effective dimensions 与 correlation。
- protocol audit 升级 v3；long-run analysis 升级 v10；structure–environment analysis 升级 v2。
- run manifest、metrics 和 evolution progress 只在新 schema 下发布资源动态 provenance。

### Validation and compatibility

- 外生 600-tick 审计空间有效维度均值 3.8670、最低 3.6497。
- 全量测试 150 passed、1 skipped。
- v0.30/v0.31 旧配置 20-tick 的 1974 个共同非计时 metrics 单元零差异，8 类知识日志 byte-identical。
- v0.30 trusted checkpoint 可由 v0.31 精确续跑；D0 未启用时新增字段和数学路径均保持惰性。

## 0.30.0

### Candidate-subject succession

- 新增 `stable-membership-subject-succession-v1`，在每次实际 group refresh 后按 stable entity ID 比较候选群组成员集合。
- 记录 formation、dissolution、split、merge、reactivation、same-token、exact-membership、member-weighted Jaccard 与 inheritance。
- 槽位复用不产生伪继承；succession edge 保持在诊断层，不写入世界主体图。
- 诊断 accounting state 支持 full checkpoint、trusted replay 与 branch clone。

### Multiscale subject–environment atlas

- 新增 `multiscale-subject-environment-atlas-v1`，使用四资源容量归一化均值、hazard 和 mortality trace 构造区域 signature。
- 支持任意多个 `normalized-fixed-count-grid-v1` scale；新主线配置使用 2×2、4×4、8×8。
- 新增 signature effective dimensions、区域距离、资源空间 CV、时间周转、实体区域有效数。
- 新增 lineage/social exposure association、covered fraction 与 region span；association 排除 singleton labels 和 social token 0。

### Offline synthesis and provenance

- 新增 `multi-seed-subject-environment-analysis-v1`，把 atlas evaluation 对齐到此前最近 group refresh，并报告跨 seed 方向。
- long-run analysis 升级为 `multi-seed-long-run-analysis-v9`。
- protocol audit 升级为 `structural-measurement-protocol-audit-v2`。
- run manifest、run metadata、resolved config 和科学解释文档发布 succession/atlas schema、scales 和 partition hashes。

### Compatibility and packaging

- 新诊断默认关闭，不改变旧配置的默认世界轨迹。
- 新增 6 个定向测试，覆盖 split/merge、stable-ID 槽位复用、多尺度异质性、association、checkpoint 和离线综合。
- `pyproject.toml` 继续显式依赖 `wheel`；发行包继续排除 `docs/archive`、缓存、Git 与构建临时目录。

## 0.29.0

### Completed event-timed matrix audit

- 审计用户提供的三批 v0.28 结果：18 个 anchors、108/108 eligible pairs、全部 stable-ID pairing 通过。
- transfer-off 对局部 active transferred roots 的负向方向在 crowding、mortality、scarcity 中重复；只解释为短期文化状态维持。
- group refresh 的 current-label cohesion 方向被 common-boundary 结果判定为评价边界主导；其余知识机制和人口结果按事件类型变化，不修改默认世界机制。

### Versioned group-label protocol

- 新增 `trusted-directed-fixed-round-min-label-v1`；配置显式发布 `group_label_schema` 和 `group_label_propagation_rounds`。
- 移除 planner 内硬编码 8 轮，仍以 8 作为旧配置兼容默认值。
- run manifest、metadata 和 scientific-validity provenance 发布 label schema、rounds、trust threshold、minimum members 与 adaptive refresh 参数。
- 新测试证明有限传播轮数会改变候选群组可达范围，协议不宣称精确无向连通分量。

### Versioned spatial-region protocol

- 新增共享 `SpatialRegionPartition` 和 `normalized-fixed-count-grid-v1`。
- local stress、event cohort、manifest 与 protocol audit 使用同一坐标映射。
- 发布 normalized topology、物理区域宽高、world-cell coverage、grid alignment 与 partition SHA-256。
- manifest 默认拒绝跨 run 混合不同 topology 或物理 region geometry；可显式 `--allow-mixed-region-partitions` 覆盖。

### Anchor selection v2

- natural-event manifest 升级为 v2，selection 升级为 `exposure-only-local-peak-selection-v2`。
- 显式记录 per-region quantile/local-peak/gap、within-region z-score ranking、distinct-region preference、candidate ranks、region bounds 与 partition hash。
- 保持旧 v1 manifest 可读；缺失几何字段标记为 legacy/inferred，不伪造 provenance。
- long-run analysis 升级为 `multi-seed-long-run-analysis-v8`。

### Protocol audit, compatibility and packaging

- 新增 `se.protocol_audit`，一份报告说明 group label、refresh、region partition 和 anchor selection。
- `pyproject.toml` build-system 显式依赖 `wheel`。
- 默认世界动力学不变；v0.28→v0.29 compatibility、trusted checkpoint resume 与完整测试报告见 `docs/v0.29/`。
- 发行包继续排除 `docs/archive`、缓存、Git 与构建临时目录。

## 0.28.0

### Intervention timing audit

- 审计用户提供的 v0.27 cohort 结果：72/72 pairs 的干预均早于名义 event tick，42 pairs 提前 30 ticks、30 pairs 提前 60 ticks。
- 48/72 pairs 在 event tick 的区域 alive 已与 baseline 不同；旧 cohort 没有 identity hashes，其余 pairs 也不能证明实体集合相同。
- 旧结果保留为 `checkpoint-immediate-v1` 估计量，不再解释为共同事件 cohort 的 post-event 效应。

### Event-timed execution

- 新增 `se.natural_event_timed_execution` 和 `natural-event-timed-execution-plan-v1`。
- 每个 source checkpoint/event tick 只重放一次 shared prefix，并保存 event checkpoint file/state SHA-256。
- baseline/interventions 从同一个 event checkpoint 开始，common boundary 与 cohort 在干预前捕获。
- 不同 event tick 不再因 source checkpoint 相同而错误共享已干预 trajectory。
- 新增 prefix/trajectory markers、hash preflight、断点续跑和 signed plan 模式。

### Cohort identity and synthesis

- event cohort 升级为 `event-region-endpoint-cohort-decomposition-v2`，新增 global/region stable-ID SHA-256。
- 每个 pair 输出 `shared-event-checkpoint-pairing-v1`，要求 alive count 与两个 identity hash 全部一致。
- result synthesis 升级为 v2，拒绝混合 checkpoint-immediate 与 event-timed 估计量。
- 自动生成 18/6/12 shared prefixes 与 72/24/48 post-event trajectories 的三份 event-timed plans。
- checkpoint-immediate execution 升级为 plan v4、marker v4、results v5，并显式写入 timing mode。

### Compatibility and packaging

- 默认世界动力学不变；v0.27→v0.28 CPU/reference 与 checkpoint 恢复兼容报告见 `docs/v0.28/`。
- 全量测试 `133 passed, 1 skipped`；新增真实 CPU event-timed smoke pairing 验证。
- `pyproject.toml` 继续无显式 `wheel`；发行包继续排除 `docs/archive`。

## 0.27.0

### Stable-ID event cohort diagnostics

- 新增 `event-region-endpoint-cohort-decomposition-v1`，在每个自然事件 tick 冻结全局与目标区域 alive stable entity IDs。
- 终点区域人口精确拆分为 cohort retained、cohort survived outside、cohort absent、existing in-migrants 与 post-event-born-at-final。
- 每个 anchor/branch 验证人口恒等式，`endpoint_population_balance_residual` 必须为 0。
- cohort 状态仅存在于执行期诊断层，不进入 checkpoint 或世界提交；实体身份按 stable ID 而非可复用 slot 判定。

### Natural-event execution v3/v4

- execution plan 升级为 v3，默认同时启用 common-boundary 与 event-cohort audit；兼容读取 v1/v2。
- trajectory marker 升级为 v3，旧 marker 不会被静默复用为含 cohort 的轨迹。
- paired results 升级为 v4，aggregation 升级为 v3，人口 delta 增加 cohort component 与 balance audit。
- 共享 checkpoint 的多个 anchor 可共用最长世界轨迹，但各自 cohort 在自己的 event tick 冻结、在自己的 horizon 截断。

### Cross-result synthesis

- 新增 `se.natural_event_result_synthesis`，合并多个同 manifest 结果集并验证重复分支的核心世界结果。
- 优先采用 cohort/common-boundary 更完整的重复分支，重新执行 seed-first aggregation，并报告 72/108 pair coverage。
- 用户提供的四份结果确认 transfer-off 对 active transferred roots 的负向作用在 crowding、mortality、scarcity 三类事件中重复。
- common-boundary 结果表明 freeze-group-refresh 的 current-label cohesion 下降主要由评价边界改变产生。
- 自动生成 64、16、48 条轨迹的三份 signed cohort follow-up plans。

### Compatibility and packaging

- 默认世界动力学不变；v0.26→v0.27 CPU 20 tick 的 1573 个非计时 metrics 单元零差异，progress byte-identical。
- v0.26 tick-10 checkpoint 可由 v0.27 恢复到 tick 20，semantic state 与连续 v0.27 一致。
- `pyproject.toml` 继续使用无显式 `wheel` 的用户版本；发行包继续排除 `docs/archive`。

## 0.26.0

### Common-boundary paired diagnostics

- 新增 `checkpoint-frozen-stable-entity-boundary-v1`，在应用干预前冻结稳定实体 ID 与群组 token。
- 局部分享流同时按分支当前标签和 checkpoint-common 标签记账；槽位复用后的新实体不会继承旧群组。
- 新增 reference internal/cross/unbounded、reference cohesion 与 boundary-definition gap。
- common boundary 只存在于诊断层，不进入策略、关系、群组、知识、环境或生命周期提交。
- checkpoint 若未与 local diagnostic window 对齐，拒绝启用共同边界。

### Natural-event results and audit

- execution plan 升级为 v2，默认启用 common-boundary audit；兼容读取 v1。
- trajectory marker 升级为 v2，防止旧轨迹被误当作含共同边界的新轨迹。
- paired results 升级为 v3，增加累计 current/reference cohesion 与 outcome audit。
- 新增 `se.natural_event_result_audit`，支持审计 v0.25 results v2 和 v0.26 results v3。
- 审计器区分操作检验、文化机制近端指标、边界定义指标和下游区域状态，并生成共同边界复跑、剩余事件复制及剩余机制消融计划。

### Input result assessment

- crowding 结果完整覆盖 6 anchors、3 seeds、3 interventions、16 trajectories。
- transfer-off 后 active transferred roots 三 seed 均下降，seed-level 平均 `-84.33`；支持短期局部文化状态维持，不支持人口收益结论。
- freeze-group-refresh 的 current-label cohesion 三 seed 均下降 `-0.2103`，但标记为 measurement-entangled，需 8-trajectory common-boundary rerun。
- neutralize-resource-affinity 的 crowded-region alive 三 seed均增加 `+7.33`，列为跨事件复制优先，不解释为固定 cohort 生存效应。

### Validation

- `126 passed, 1 skipped`；跳过真实 CUDA/CuPy 设备测试。
- v0.25→v0.26 默认 CPU 20 tick：1570 个共同非计时 metrics 单元零差异。
- `evolution_progress.jsonl` 与 7 类知识日志 byte-identical。
- v0.25 tick-10 checkpoint 由 v0.26 恢复至 tick 20，内部 simulation state 与连续 v0.26 一致。

## 0.25.0

### Manifest execution

- 新增 `se.natural_event_execution`，从已签名 v0.24 manifest 构造独立执行计划。
- 支持跨机器 `OLD=NEW` 路径前缀映射，同时保留原始 manifest 不变。
- 执行前分别校验 checkpoint、progress 和 resolved config SHA-256。
- 相同 checkpoint hash 与 intervention 的多个锚点共享最长轨迹；用户 manifest 从 126 条 naive branches 降为 112 条 trajectories。
- 每条完成轨迹写入可审计 marker，支持安全断点续跑；不完整目录默认拒绝覆盖。
- paired results 升级为 v2，增加先 seed 内平均、再跨 seed 汇总的方向统计，避免 anchor 伪重复。

### Packaging and documentation

- `pyproject.toml` 采用用户提供的 project metadata、console script、dev dependency 和 pytest 配置。
- build-system 移除显式 `wheel`，当前环境仍可成功生成 wheel。
- 新发行压缩包不包含 `docs/archive`；根目录只保留稳定入口和运行脚本。
- v0.25 实现、manifest、执行计划与验证报告集中在 `docs/v0.25/`。

### Validation

- `123 passed, 1 skipped`；跳过真实 CUDA/CuPy 设备测试。
- v0.24→v0.25 默认 CPU 20 tick：1606 个共同非计时 metrics 单元零差异，`evolution_progress.jsonl` byte-identical。
- v0.25 从 v0.24 tick-10 `.sechk` 恢复到 tick 20，内部 simulation state 与连续 v0.25 逐字段一致。

## 0.24.0

### Scientific workflow

- 新增 `se.natural_event_matrix`，支持跨 seed 的 scarcity、crowding、mortality 自然事件锚点规划与可选执行。
- 新增 `exposure-only-local-peak-selection-v1`：锚点选择只读取暴露、区域 alive、tick 和 checkpoint 可用性；明确排除凝聚度、传播、文化根、谱系和动作结果字段。
- manifest 记录 progress、resolved config、checkpoint 和完整计划 SHA-256；可检测执行前静默修改。
- 可选 long-run analysis JSON 只保存为 rationale/audit，`used_for_anchor_selection=false`。
- 每个 anchor 逐项记录 intervention eligibility；当前旗舰配置会正确将 danger-evidence neutralization 标记为不可识别。

### Interventions

- 新增 `freeze-group-refresh`（aliases: `group-refresh-off`, `freeze-groups`）。
- 干预保持已有群组标签，不再执行周期或 adaptive refresh；死亡成员正常清除，新生体保持未分组。
- 新状态进入完整 checkpoint、恢复、内存 clone、metrics、evolution progress 和 intervention history。

### Documentation

- 重写根 `README.md`，移除 v0.4 实现状态叙述。
- 将旧 `IMPLEMENTATION_STATUS.md` 与后续状态文档整合为 `docs/PROJECT_STATUS.md`。
- 重写 `docs/SCIENTIFIC_ISSUES.md`，按当前知识层、局部文化、mortality trace、adaptive groups、环境插件和 GPU 边界更新。
- 根目录的历史报告和旧文档原样移入 `docs/archive/pre-v0.24/`。
- v0.24 的输入分析、实现说明、兼容报告和测试报告集中于 `docs/v0.24/`。

### Validation

- `120 passed, 1 skipped`；跳过真实 CUDA/CuPy 设备测试。
- v0.23→v0.24 默认路径 20 tick：341 个共同 metrics 字段中，排除 13 个计时字段后零差异；knowledge event log byte-identical。
- v0.24 成功恢复 v0.23 `.sechk`，共同非计时终点与连续 v0.24 一致。

## 0.23.0

- 增加 `additive-environment-field-process-v1` 的低耦合标量场插件边界。
- 将 moving Gaussian hazard 从核心逻辑降级为默认关闭的 synthetic observation/entertainment 兼容插件。
- 长期分析升级为 v7，记录环境过程 provenance。

## 0.22.0

- 增加 moving-hazard 兼容机制、遗传 direct/trace danger evidence mixture 与中和干预。
- 长期分析 v6 增加证据权重、mortality trace 和 group refresh audit。

## 0.21.0

- 增加 local decaying mortality trace 与 adaptive topology group refresh。
- 完成 checkpoint/replay 与 NumPy/simulated-device 验证。

## 0.20 及更早

详细历史材料保存在旧版本发行包中。当前发行包不再复制 `docs/archive`。