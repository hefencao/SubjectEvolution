# v0.20 局部文化传播短周期控制矩阵

## 条件

- CPU strict-reference；
- seed 10001；
- 120 ticks；
- 200 initial / 512 capacity；
- 4×4 分析区域；
- 空间异步多资源、固定预算亲和、L2、工作记忆、遗传 Top-k、有代价传播；
- 每 20 ticks 记录并保存完整 checkpoint；
- A/B 两次独立重复。

## 终点

| 指标 | A | B |
|---|---:|---:|
| Alive | 430 | 430 |
| Transfer proposals | 111 | 111 |
| Attempts | 111 | 111 |
| Commits | 89 | 89 |
| Bytes | 5,640 | 5,640 |
| Same-region commits | 76 | 76 |
| Cross-region commits | 13 | 13 |
| Active transferred roots | 85 | 85 |
| Effective transferred roots | 84.0455 | 84.0455 |
| Multi-region active roots | 0 | 0 |

## 确定性

- 8 类核心日志 byte-identical；
- 289 个非计时 metrics 字段一致；
- tick 20/40/60/80/100/120 的 38 个公开 checkpoint 数组一致；
- tick 120 完整 checkpoint 的 331 个数组叶和 26,937 个标量叶一致；
- tick 60 恢复到 tick 120 的权威状态一致，唯一差异是恢复 provenance lineage。

## 解释边界

只有 6 个长期窗口。短期相关和手工事件分支用于验证统计与因果工具链，不能替代用户三 seed、1500-tick 长期实验。
