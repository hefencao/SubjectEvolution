# Subject Evolution 项目状态（v0.9.0）

## 当前完成阶段

| 功能 | 状态 |
|---|---|
| 动态知识副本、容量、维持与损坏 | K1 已完成 |
| 有代价知识交换与传播谱系 | K1 已完成 |
| 局部五维后果记录与经验更新 | K2 已完成 |
| 知识稀疏残差进入策略 | K3 已完成 |
| 知识内容谱系与候选主体图诊断 | K4 已完成 |
| checkpoint 全世界恢复 | **v0.9.0 已完成** |
| 离线反事实分支重放 | **v0.9.0 已完成** |
| 完整设备驻留世界循环 | 未实现 |
| 完整主体图数据库及任意嵌套主体 | 未实现 |
| 信息模板寄生主体 | 未实现 |
| 完整主体性评分 | 未实现 |
| Hero 强化学习 | 未实现 |
| 任意信息通道 schema | 未实现 |

## v0.9.0 概要

新增 `subject-evolution-full-checkpoint-v1`。`.sechk` 保存完整实体容量状态、环境/信息场、延迟队列、关系、主体图、K1–K4 知识状态、累计统计、干预历史和演化进度，可在新进程中精确继续。

新增：

- `Simulation.save_full_checkpoint()`；
- `Simulation.from_checkpoint()`；
- `python -m subject_evolution.replay`；
- 通用 CLI 的 `--resume-checkpoint` 与 `--until-tick`；
- checkpoint SHA-256 与 replay lineage provenance；
- 从磁盘共同历史执行 paired counterfactual。

旧 `.npz` 仍为分析快照，不能恢复。完整 `.sechk` 使用可信 pickle，只能加载本项目自己生成的文件。完整 checkpoint 默认关闭，避免对大规模正式运行产生隐式存储成本。

## 短周期验证

本轮未运行 500 ticks。

- CPU、seed 10001、256 初始实体、20 ticks；
- tick 10 保存 checkpoint，恢复后继续到 tick 20；
- 连续与恢复的完整语义状态 0 差异；
- 共同非计时 metrics 完全一致；
- 磁盘恢复 baseline/intervention 与同 tick 内存 clone 分支完全一致；
- 离线 `reverse-environment` 分支最终 alive 279 vs 277，证明分支独立生效；
- 39 tests passed，1 个真实 CUDA 测试跳过。

## CPU/GPU 状态

v0.6.4 的 reference-order signal/harvest 归约和 v0.6.5 周期位置规范化继续保留。完整 checkpoint 在 hybrid runtime 存在时先把环境和信息同步回 host，恢复后再重建 runtime 并同步实体/社会/字段状态。

当前容器没有 CUDA，因此真实 hybrid GPU 的 checkpoint 保存、跨进程恢复与后续 parity 仍需在 GPU 主机验证。CPU reference 的完整恢复已经逐状态证明。

## 下一阶段建议

基础设施下一优先级可选：

1. 将现有 body/lineage/social/knowledge 候选节点统一为可持久化、可查询的通用主体图数据库；
2. 支持任意嵌套主体，但保持 proposal → intent → resolution → commit 控制边界；
3. 建立多 seed、预注册环境梯度和 checkpoint 分支实验，开始验证候选知识主体指标的因果稳定性。

信息模板寄生主体、Hero 强化学习、任意信息通道 schema 和完整设备驻留循环仍应作为独立阶段。
