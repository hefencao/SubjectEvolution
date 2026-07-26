# v0.25 文档索引

- `MANIFEST_ASSESSMENT.md`：用户 18-anchor manifest 的结构、尺度和执行量评估。
- `NATURAL_EVENT_EXECUTION_IMPLEMENTATION.md`：执行计划、路径映射、预检、去重、续跑和聚合语义。
- `NATURAL_EVENT_MATRIX_MANIFEST.json/md`：用户生成的原始已签名 manifest。
- `NATURAL_EVENT_EXECUTION_PLAN.json/md`：由该 manifest 生成的 112-trajectory 执行计划。
- `LOCAL_ENVIRONMENT_PREFLIGHT.json`：当前构建环境预检；因没有用户绝对路径下的原始 run，预期为 not ready。
- `V024_V025_COMPATIBILITY_REPORT.json`：默认运行轨迹兼容。
- `V024_CHECKPOINT_V025_RESUME_REPORT.json`：旧 checkpoint 恢复兼容。
- `PACKAGING_VALIDATION_REPORT.json`：pyproject、wheel 和压缩包布局验证。
- `FINAL_TEST_REPORT.txt`：最终测试摘要。
