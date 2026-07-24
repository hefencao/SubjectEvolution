# Subject Evolution 项目状态（v0.11.0）

## 当前完成阶段

| 功能 | 状态 |
|---|---|
| 动态知识副本、容量、维持与损坏 | K1 已完成 |
| 有代价知识交换与传播谱系 | K1 已完成 |
| 局部五维后果记录与经验更新 | K2 已完成 |
| 固定五维知识 residual 接入策略 | K3 已完成 |
| 知识内容谱系与候选主体图诊断 | K4 已完成 |
| checkpoint 全世界恢复与离线分支重放 | v0.9.0 已完成 |
| 可变长度潜知识 + 遗传量化线性路由器 | v0.10.0 L1 已完成 |
| 可变长度潜知识 + 遗传量化两层 MLP | **v0.11.0 L2 已完成** |
| MLP 计算能耗物理结算 | 未实现 |
| 潜坐标/路由器局部学习 | 未实现 |
| 持久设备驻留 latent arena | 未实现 |
| 完整设备驻留世界循环 | 未实现 |
| 完整主体图数据库及任意嵌套主体 | 未实现 |
| 信息模板寄生主体 | 未实现 |
| 完整主体性评分 | 未实现 |
| Hero 强化学习 | 未实现 |
| 任意信息通道 schema | 未实现 |

## v0.11.0 概要

新增独立 L2 schema。每个承载体保留完整 L1 线性路由前缀，并追加一个遗传编码、整数定点的两层 MLP。输入为变长潜内容的固定投影、四维公开状态和三维可靠性/来源元数据，输出仍只发布到公开 action-logit residual 接口。

激活为 integer hard-tanh，不使用后端相关 transcendental 函数。每 tick 同时评估 genetic-only、L1 shadow 和 L2 动作，记录饱和、裁剪、隐藏活动和量化贡献。

## 兼容性

v0.10.0 与 v0.11.0 在 L1 配置下：

- 167 个共同非计时 metrics 字段一致；
- outcome 日志 19 个共同字段逐行一致；
- contribution 日志 20 个共同字段逐行一致；
- tick 15/30 的 35 个共同 checkpoint 数组完全一致。

L2 关闭时没有改变 K1–K4 或 L1 世界语义。

## 验证

- 50 tests：49 passed，1 个真实 GPU 测试因无 CUDA 跳过；
- L2 private 与 exchange 各双重复，177 个非计时指标、全部核心日志和 35 个 checkpoint 数组一致；
- L2 完整 `.sechk` 恢复与连续世界状态一致；
- L1 shadow、hard-tanh 饱和、输出裁剪和独立 schema 有专项测试。

## CPU/GPU 状态

L2 采用 CPU-reference 量化和整数 backend 路由，避免 `tanh/exp` 差异。关键乘加按固定维度顺序执行，L1 shadow 和 L2 都在量化边界发布。

当前容器无 CUDA，真实 GPU 多 tick L2 parity 未验证。正式 scientific GPU run 仍应使用 `strict-reference`；`hybrid-accelerated` 只用于显式 parity 和性能实验。

## 下一步建议

1. 在真实 GPU 上完成 L2 world parity；
2. 将 MLP 计算量转换成明确物理能量成本，做 L1/L2 预算匹配；
3. 做多 seed、activation clip、hidden width、residual scale 和 latent length budget sweep；
4. 用 `.sechk` 对潜内容、L1 prefix、MLP hidden units 做离线消融；
5. 之后再考虑潜坐标或路由器的局部学习。
