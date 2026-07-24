# Subject Evolution 项目状态（v0.10.0）

## 当前完成阶段

| 功能 | 状态 |
|---|---|
| 动态知识副本、容量、维持与损坏 | K1 已完成 |
| 有代价知识交换与传播谱系 | K1 已完成 |
| 局部五维后果记录与经验更新 | K2 已完成 |
| 固定五维知识 residual 接入策略 | K3 已完成 |
| 知识内容谱系与候选主体图诊断 | K4 已完成 |
| checkpoint 全世界恢复与离线分支重放 | v0.9.0 已完成 |
| 可变长度潜知识 + 可演化线性路由器 | **v0.10.0 L1 已完成** |
| 小型非线性潜路由器 | 未实现，L2 |
| 持久设备驻留 latent arena | 未实现 |
| 完整设备驻留世界循环 | 未实现 |
| 完整主体图数据库及任意嵌套主体 | 未实现 |
| 信息模板寄生主体 | 未实现 |
| 完整主体性评分 | 未实现 |
| Hero 强化学习 | 未实现 |
| 任意信息通道 schema | 未实现 |

## v0.10.0 概要

新增独立潜知识 schema。内容使用变长 int16 SoA，默认长度等级为 4/8/16/32；损坏变体可以在相邻等级扩张或收缩。实体使用遗传编码的量化线性路由器，将潜内容、K2 本地五维后果和四维公开状态发布到原有 action-logit residual 接口。

没有外部集中训练器、全局 reward 或隐藏 action replacement。潜表示的解释目标是来源、贡献和反事实可审计，而非强制每个坐标具有人为名字。

## 兼容性

潜路径默认关闭。v0.9.0 与 v0.10.0 的 latent-off K4 20-tick 对照中：

- 185 个共同非计时 metrics 字段一致；
- 52 个共同 checkpoint 数组逐数组一致；
- K1–K4 世界日志一致；
- 原贡献日志 16 个字段逐行一致；
- v0.10.0 只新增四个潜路由诊断列。

## 验证

- 46 tests：45 passed，1 个真实 GPU 测试因无 CUDA 跳过；
- 私有与交换条件各双重复，所有非计时 metrics、知识/传输/后果/贡献日志及 35 个 checkpoint 数组一致；
- 完整 `.sechk` 恢复后的潜世界与连续运行完整状态一致；
- 变体长度变化、真实字节容量仲裁、copy-order 稳定聚合均有测试。

## CPU/GPU 状态

潜后果、状态和使用强度先通过 CPU reference 量化；GPU 负责整数变长桶路由。v0.10.0 同时修复 hybrid GPU policy 之前未传入知识 plan 的遗漏。

当前容器无 CUDA，真实 GPU 上的潜路由多 tick parity 未完成。正式 scientific GPU run 仍应使用 strict-reference，hybrid 仅用于显式 parity/性能实验。

## 下一步建议

1. 在真实 GPU 上运行潜路由 world parity，定位任何首差异；
2. 做 residual scale、长度预算、hidden width 与多 seed sweep；
3. 实现 L2 小型非线性路由器，但保持独立 schema 和量化发布边界；
4. 将 host latent arena 改为增量 device-resident buckets；
5. 使用 checkpoint 消融评估潜内容、潜维度和路由参数的因果贡献。
