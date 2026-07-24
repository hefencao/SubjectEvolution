# K3 短周期对照报告

## 范围

本报告用于验证 K3 实现、确定性和 K2 兼容边界，不用于宣称长期适应优势。

共同设置：CPU、seed 10001、30 ticks、初始 500 个体、最大 768，在 tick 15 和 30 保存检查点。每个条件独立复跑两次。

| 条件 | alive | births | influenced entity-ticks | influenced action cells | changed actions | transfers |
|---|---:|---:|---:|---:|---:|---:|
| K2 control | 608 | 108 | 0 | 0 | 0 | 228 |
| K3 private | 609 | 109 | 10041 | 15493 | 31 | 0 |
| K3 exchange | 608 | 108 | 10362 | 15855 | 29 | 224 |

## 确定性

三个条件均满足：

- 非计时 metrics 差异为 0；
- knowledge event 日志完全一致；
- K3 条件的 policy contribution 日志完全一致；
- tick 15/30 的 32 个 checkpoint 数组逐数组一致。

## 解释边界

- K2 control 不产生知识 residual 或 action change；
- K3 private 验证私有经验能够形成稀疏 residual；
- K3 exchange 验证有代价交换知识可在显式可靠性/验证折扣下参与 residual；
- changed actions 使用同一随机流比较 genetic-only 与 combined logits；
- 30 ticks、单 seed 的差异不能被解释为稳定选择优势或主体性证据。

机器可读完整结果见 `K3_VALIDATION_REPORT.json`，逐条件摘要见 `K3_RUN_SUMMARY.csv`。
