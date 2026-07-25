# Changelog

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

详细历史变更、实现报告和兼容矩阵保存在：

```text
docs/archive/pre-v0.24/
```

这些文件按原文件名保存，可能包含当时有效、现在已经过时的状态描述。
