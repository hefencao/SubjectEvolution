# L2 非线性潜路由短周期对照（v0.11.0）

## 设置

- CPU reference；
- seed 10001；
- 30 ticks；
- initial entities 500；
- max entities 768；
- checkpoint tick 15 / 30；
- residual bound 0.75；
- latent levels 4/8/16/32；
- projection width 8；
- MLP hidden width 8。

## 结果

| 条件 | alive | births | 内容 / 副本 | 变体 | genetic→active 路由动作改变 | L1 shadow→L2 动作改变 | 饱和隐藏单元 | 输出裁剪事件 | 交换提交 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| L1 linear private | 604 | 104 | 4328 / 4386 | 0 | 2654 | 0 | 0 | 0 | 0 |
| L2 MLP private | 605 | 105 | 4223 / 4281 | 0 | 2545 | 3560 | 48388 | 23799 | 0 |
| L2 MLP costed exchange | 607 | 107 | 4170 / 4358 | 10 | 2540 | 3553 | 51305 | 24246 | 233 |

最终潜长度分布：

| 条件 | 4D | 8D | 16D | 32D |
|---|---:|---:|---:|---:|
| L1 linear private | 1196 | 1149 | 1042 | 941 |
| L2 MLP private | 1094 | 1118 | 1051 | 960 |
| L2 MLP exchange | 1099 | 1092 | 1057 | 922 |

## 确定性

L2 private 和 L2 exchange 均独立运行两次：

- 177 个非计时 metrics 字段逐值一致；
- `knowledge_events.jsonl` byte-identical；
- outcome、transfer、policy contribution 和 evolution 日志 byte-identical；
- tick 15 和 tick 30 的 35 个 checkpoint 数组逐数组一致。

## 解释限制

L2 的饱和和裁剪非零，说明网络确实进入非线性区间；L1 shadow 与 L2 在同一状态、同一随机抽样下产生大量不同动作，说明 L2 不是线性路由的无效重编码。

这些 30-tick 单 seed 结果不能证明 L2 比 L1 更有长期适应优势。alive 差异很小，也未控制 MLP 计算能耗。后续需要多 seed、参数 sweep、计算预算匹配和 checkpoint 消融。
