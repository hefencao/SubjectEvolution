# Changelog

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
- 新增 `subject_evolution.natural_event_result_audit`，支持审计 v0.25 results v2 和 v0.26 results v3。
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

- 新增 `subject_evolution.natural_event_execution`，从已签名 v0.24 manifest 构造独立执行计划。
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

- 新增 `subject_evolution.natural_event_matrix`，支持跨 seed 的 scarcity、crowding、mortality 自然事件锚点规划与可选执行。
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
