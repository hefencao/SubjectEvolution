# v0.24 patch notes

## Source

- 新增 `src/subject_evolution/natural_event_matrix.py`。
- `interventions.py` 注册 `freeze-group-refresh`。
- `simulation.py` 增加群组刷新消融状态、checkpoint/clone 恢复、GPU 准备短路、更新跳过和诊断字段。
- 版本号更新为 0.24.0。

## Tests

- 新增暴露盲选、manifest hash、intervention eligibility、旧 checkpoint 和 freeze-group-refresh 测试。
- 增加 `tests/__init__.py`，避免环境中的外部 `tests` 包遮蔽本地测试模块。

## Documentation

- 重写稳定 README、PROJECT_STATUS、SCIENTIFIC_ISSUES、CHANGELOG 和 ARCHITECTURE。
- 所有 v0.24 报告放入 `docs/v0.24/`。
- 旧根目录报告归档到 `docs/archive/pre-v0.24/`。
