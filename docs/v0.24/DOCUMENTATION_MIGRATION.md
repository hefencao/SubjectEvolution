# 文档迁移

## 新布局

```text
README.md                         稳定入口与运行方式
docs/PROJECT_STATUS.md            当前实现状态
docs/SCIENTIFIC_ISSUES.md         当前科学问题与解释边界
docs/CHANGELOG.md                 版本变更摘要
docs/ARCHITECTURE.md              稳定架构边界
docs/v0.24/                       v0.24 输入、实现和验证报告
docs/archive/pre-v0.24/root/      旧根目录文档与报告
docs/archive/pre-v0.24/docs/      旧 docs 内容
```

## 迁移原则

- 历史文件不删除、不改写，保持原文件名以便追溯；
- 历史文件不再作为当前状态入口；
- `IMPLEMENTATION_STATUS.md` 不再单独维护，其仍有价值的实现边界已合并进 `docs/PROJECT_STATUS.md` 与 `docs/ARCHITECTURE.md`；
- 每个新版本只在 `docs/vX.Y/` 增加该版本报告；
- 根目录以后不再放测试报告、兼容 JSON、阶段实现说明或方向评估。
