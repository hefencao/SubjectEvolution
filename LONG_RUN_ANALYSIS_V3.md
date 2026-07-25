# 长期分析 v3

Schema：`multi-seed-long-run-analysis-v3`

## 相比 v2 的修复

- 文化传播可解释性只由真实成功提交决定；
- 配置概率大于 0 但累计提交缺失/为 0 时给出明确警告；
- 输出 proposals、attempts、committed、bytes 和提交率；
- 输出跨 lineage/group 提交和 transferred-root 指标；
- 按 rise、decline、peak、trough 描述传播窗口；
- 只有传播可解释时才计算文化传播相关。

## 旧报告兼容

v0.17 及更早 `evolution_progress` 缺少累计传播字段时，v3 不会假定传播为零，也不会因配置概率大于 0 自动宣称文化传播可解释。应回到原运行目录读取：

- `metrics.csv`；
- `knowledge_transfers.csv`；
- `run_metadata.json`；

或用 v0.18 重新运行。

## 相位统计边界

rise/decline/peak/trough 汇总是描述性分层，不是自动因果识别。正式因果判断仍应使用同 checkpoint、同 keyed randomness 的相位反事实分支。
