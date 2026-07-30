# Subject Evolution v0.26

v0.26 不修改世界规则。它针对 v0.25 crowding 配对干预结果暴露出的测量边界问题，增加 checkpoint-common boundary 诊断与结果审计。

主要入口：

```bash
python -m subject_evolution.natural_event_result_audit \
  --results analyses/natural_event_execution/natural_event_matrix_results.json \
  --execution-plan analyses/natural_event_execution/natural_event_execution_plan.json \
  --manifest analyses/natural_event_matrix/natural_event_matrix_manifest.json \
  --output analyses/natural_event_result_audit
```

v0.26 新生成的 `natural_event_execution` 计划默认启用共同边界诊断。旧 v0.25 execution plan 仍可加载和审计，但其轨迹不含共同边界字段；对 `freeze-group-refresh` 的 cohesion 解释需要按 v0.26 计划复跑。

本目录包含用户结果审计、三类后续执行计划、实现说明、兼容和验证报告。

## 本版本文档

- `COMMON_BOUNDARY_DIAGNOSTICS.md`
- `RESULT_AUDIT_IMPLEMENTATION.md`
- `CROWDING_RESULT_ASSESSMENT.md`
- `MIGRATION_V026.md`
- `FINAL_TEST_REPORT.txt`
- 输入结果审计与三份带哈希的后续执行计划
