# Subject Evolution 项目状态（v0.18.0）

## 已完成阶段

| 功能 | 状态 |
|---|---|
| K1–K4 动态知识、局部后果、策略 residual、内容谱系诊断 | 完成 |
| v0.9 完整 checkpoint、恢复和离线反事实 | 完成 |
| v0.10–v0.12 可变潜知识、L1/L2 路由和物理计算成本 | 完成 |
| v0.13 工作记忆与稀疏 stable Top-k | 完成 |
| v0.14 遗传 Top-k 容量与 checkpoint 消融 | 完成 |
| v0.15 空间异步四资源生态位与固定预算亲和 | 完成 |
| v0.16 长期选择、世系—群组、知识根诊断与多 seed 工具 | 完成 |
| v0.17 去趋势分析与生态相位 checkpoint 反事实 | 完成 |
| v0.18 有代价传播审计、窗口/累计统计与 transfer-only 文化谱系 | **完成** |
| v0.17 世界语义兼容 | **完成** |
| 真实 CUDA v0.18 world parity | 未完成 |
| 三 seed 完整相位传播因果矩阵 | 未运行 |
| 潜坐标/路由器局部学习 | 未实现 |
| 持久 device-resident latent arena | 未实现 |
| 完整通用主体图数据库与任意嵌套主体 | 未实现 |

## 用户三 seed、1500-tick 输入的可靠结论

有代价传播配置下，三个 seed 在 tick 1500 的端点为：

- alive：`1334–1386`；
- effective founder lineages：`15.14–25.76`；
- strategy effective dimensions：`13.96–21.22`；
- action entropy：`1.725–1.754`；
- boundary cohesion：`0.350–0.447`；
- resource-affinity effective dimensions：`2.11–2.82`。

多元环境仍明显延缓旧单资源世界中的功能维度坍缩。死亡压力与凝聚度的水平/偏相关在三 seed 中同向，但一阶差分较弱，不能解释成“压力必然令下一窗口凝聚度增长”。

## v0.17 传播诊断错误与 v0.18 修复

用户附上的 v2 分析同时出现：

- 配置传播概率 `0.1`；
- `knowledge_transfer_committed_final = 0`；
- `knowledge_cultural_spread_interpretable = true`。

审计确认这是诊断 schema 问题：v0.17 的长期进度未写累计传播字段，分析器把缺失字段默认成 0；同时只要配置概率大于 0就错误地标记文化传播可解释。旧知识根指标还混入宿主私有经验，不能作为文化复制证据。

v0.18 现在记录：

- proposal、attention 后 attempt、delivery/loss/corruption、commit 和真实字节；
- duplicate、capacity、energy、attention 等拒绝原因；
- same/cross/unknown founder-lineage 与 group 提交；
- sender/receiver 能耗；
- 仅由真实 transfer 副本构成的 transferred-root 多样性；
- checkpoint 前没有成功传播时，`disable-transfer` 反事实标记为不可识别。

## v0.18 120-tick 验证

同一正式配置、seed 10001、CPU strict-reference：

| 指标 | 数值 |
|---|---:|
| 传播 proposals | 546 |
| attention 后 attempts | 545 |
| 成功 commits | 447 |
| 提交率 | 82.02% |
| 提交字节 | 26,920 |
| 跨 founder-lineage commits | 396 |
| 同 founder-lineage commits | 51 |
| 跨 group commits | 2 |
| active transferred roots | 391 |
| effective transferred roots | 365.4454 |

多数早期提交发生在 group 形成前，因此 group 分类 unknown 较多；这不表示事件丢失。

## 验证状态

- 90 tests：89 passed，1 个真实 CUDA 测试因无设备跳过；
- 120-tick 同 seed 双重复：核心日志 byte-identical；
- 289 个共同非计时 metrics 字段一致；
- tick 60/120 的 38 个 checkpoint 数组 bitwise identical；
- 从 tick 60 `.sechk` 恢复到 tick 120 与连续运行完全一致；
- v0.17/v0.18 30-tick 无行为修改兼容：136 个长期进度共同字段和 10 个 transfer 共同语义字段一致，知识事件日志一致；metrics 差异仅为 wall-clock 计时字段；
- 真实 CUDA v0.18 尚未验证。

## 下一步优先级

1. 对原三 seed 运行目录使用 v0.18 原始 `knowledge_transfers.csv`/metrics 回填真实累计传播；旧 v2 汇总文件本身无法恢复缺失事件数；
2. 用 v0.18 schema 运行 `3 seeds × 600–1500 ticks`，分析 transfer-only 文化根的持续性、跨世系与跨 group 扩散；
3. 在 rise/peak/decline/trough checkpoint 执行 `disable-knowledge-transfer` 配对分支；
4. 区分“停止未来传播”与“消融既有 transfer-derived 副本”的因果效应；
5. 完成真实 CUDA v0.18 parity；
6. 只有文化传播与环境生态位的因果矩阵完成后，再考虑新增主体控制结构。

暂不采用：配置概率大于 0即宣称传播、将私有经验根当作文化谱系、按谱系奖励、提高跨组惩罚、简单提高 mutation rate、全局类别 embedding 或更深网络。
