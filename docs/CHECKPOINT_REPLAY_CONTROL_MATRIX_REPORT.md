# v0.9.0 checkpoint / replay 短验证报告

## 设置

- backend：CPU
- seed：10001
- 初始实体：256
- 最大实体：384
- 总 horizon：20 ticks
- 完整 checkpoint：tick 10、20
- K4 candidate tracking：开启

## 连续运行与恢复运行

| 比较 | 结果 |
|---|---|
| tick 20 完整语义状态 | 完全一致，0 个差异 |
| tick 15/20 共同非计时 metrics | 完全一致 |
| 实体、环境、信息、关系、主体图 | 完全一致 |
| K1–K4 知识状态与候选累计量 | 完全一致 |
| 待 flush 信号队列和 pending messages | 完整 checkpoint 覆盖 |

计时字段不要求一致，因为恢复运行使用新的进程/输出窗口。

## 离线反事实

从同一个 tick 10 checkpoint 创建：

- baseline：不干预；
- intervention：`reverse-environment`，tick 10 应用；
- 共同随机数：是；
- 最终 tick：20。

结果：

| 指标 | baseline | intervention | delta |
|---|---:|---:|---:|
| alive | 279 | 277 | -2 |
| mean_energy | 2.063... | 2.069... | +0.0055766 |

该短实验只验证离线分支机制确实产生独立世界后果，不用于推断长期生态或演化结论。

## 自动测试

- 39 passed；
- 1 skipped：当前容器没有 CUDA/CuPy；
- 包含连续/恢复一致、磁盘/内存分支一致、周期自动写 `.sechk`。
