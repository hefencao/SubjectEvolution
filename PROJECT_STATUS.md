# Subject Evolution 项目状态（v0.16.0）

## 已完成阶段

| 功能 | 状态 |
|---|---|
| K1–K4 动态知识、局部后果、策略 residual、内容谱系诊断 | 完成 |
| v0.9 完整 checkpoint、恢复和离线反事实 | 完成 |
| v0.10–v0.12 可变潜知识、L1/L2 路由和物理计算成本 | 完成 |
| v0.13 工作记忆与稀疏 stable Top-k | 完成 |
| v0.14 遗传 Top-k 容量与 checkpoint 消融 | 完成 |
| v0.15 空间异步四资源生态位与固定预算亲和 | 完成 |
| v0.16 长期选择、世系—群组和知识根谱系诊断 | **完成** |
| v0.16 可中断多 seed 顺序执行与离线聚合 | **完成** |
| v0.15 世界语义兼容 | **完成** |
| 真实 CUDA v0.16 world parity | 未完成 |
| 多 seed 600–3000 tick 新生态长期验证 | 未完成 |
| 潜坐标/路由器局部学习 | 未实现 |
| 持久 device-resident latent arena | 未实现 |
| 完整通用主体图数据库与任意嵌套主体 | 未实现 |

## 当前方向

旧环境的两个 3000-tick seed（其中 seed 10002 目前只有二次分析摘要）均显示人口周期、采集倾向和策略功能维度下降，但最终 founder-lineage 集中度存在显著路径分叉。这个差异有科学价值，但仅靠 `effective_lineages` 和 `benefit_boundary_cohesion` 不能证明世系竞争导致群体凝聚。

v0.16 不再增加控制结构，而是增加直接测量：

- 当前群组与 founder lineage 的 NMI、纯度和实体对富集；
- 死亡/出生压力窗口；
- eligible carrier、成功亲本和子代的活跃形态性状均值；
- 选择差和代际传递差；
- 活跃知识根内容的有效谱系、最大持有率及其跨遗传世系/群组传播；
- 多 seed 运行索引与离线相关分析。

所有新增字段均为观察性诊断，不进入策略、结算、环境或知识路由。

## 本轮输入评估

用户提供的两份 120-tick v0.15 结果显示：

- 无亲和条件活跃形态有效维度约 `1.96`；
- 固定预算亲和条件约 `5.72`；
- 亲和子空间有效维度约 `2.96`；
- 但策略有效维度、动作熵、人口和 founder-lineage 指标在 120 tick 内差异仍很小。

因此这些结果证明新增环境轴被使用，不证明长期多样性改善。

## 验证

- 80 tests：79 passed，1 个真实 CUDA 测试因无设备跳过；
- v0.15 与 v0.16 的 120-tick affinity 条件：98 个共同进度字段一致到 `4.27e-14`，38 个 checkpoint 数组 bitwise identical；
- v0.16 短 seed 重复：`evolution_progress.jsonl` 与 `knowledge_events.jsonl` byte-identical，280 个 metrics 列中除 12 个计时列外其余 268 列完全一致；
- checkpoint 恢复保持长期选择累计窗口；
- 多 seed 执行器支持逐 seed 增量索引、跳过完成目录和显式覆盖未完成目录；
- 真实 CUDA v0.16 仍未验证。

## 下一步优先级

1. 使用 v0.16 long-run 配置运行 `3–5 seeds × 600–1500 ticks`；
2. 至少为 seed 10001/10002 重跑或续跑，获得 lineage-group pair enrichment 和知识根谱系数据；
3. 在人口上升、峰值、下降和谷值 checkpoint 分别执行 memory、selection、knowledge residual 和 affinity 消融；
4. 比较遗传有效谱系与知识有效根谱系是否同步坍缩；
5. 若多个 seed 中亲和维度仍迅速坍缩，再增加移动危险源或局部生态工程；
6. 在真实 GPU 上完成 v0.16 parity。

暂不采用：按谱系奖励、强制多样性、提高跨组惩罚、简单提高 mutation rate、全局类别 embedding 或更深网络。

GPU 后端要求 CuPy >= 12、匹配 CUDA runtime、可用 CUDA GPU，以及 CuPy Thrust 支持。
