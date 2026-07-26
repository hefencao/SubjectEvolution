# v0.26 patch notes

- 新增 checkpoint-common stable-entity group boundary，只用于局部分享流诊断。
- natural-event execution plan 升级为 v2，默认启用 common-boundary audit；兼容读取 v1 plan。
- trajectory marker 升级为 v2，防止把缺少共同边界字段的旧轨迹错误复用为 v0.26 结果。
- paired results 升级为 v3，新增累计 current/reference cohesion、boundary-definition gap 与 outcome audit。
- 新增 `subject_evolution.natural_event_result_audit`，支持审计 v2/v3 结果并生成预注册后续计划。
- 默认普通世界运行不启用共同边界，世界轨迹和原有日志保持不变。
