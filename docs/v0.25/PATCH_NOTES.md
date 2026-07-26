# v0.25 patch notes

- 新增 `src/subject_evolution/natural_event_execution.py`。
- 新增已签名 manifest 的路径映射、哈希预检、轨迹去重、断点续跑和 seed-level 汇总。
- 新增 `tests/test_natural_event_execution.py`。
- 版本号更新为 0.25.0。
- `pyproject.toml` 采用用户提供的 project metadata、console script、dev dependency 和 pytest 配置；构建依赖移除显式 `wheel`。
- 根目录历史报告不再进入新项目包；`docs/archive` 不进入压缩包。
- v0.24 manifest schema 和既有执行入口保持可用。
