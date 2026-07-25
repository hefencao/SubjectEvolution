# Subject Evolution 项目状态（v0.17.0）

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
| v0.17 去趋势长期分析与跨 seed 方向一致性 | **完成** |
| v0.17 生态相位 checkpoint 反事实规划与执行 | **完成** |
| v0.17 亲和、知识策略与传播的独立科学消融 | **完成** |
| v0.16 世界语义兼容 | **完成** |
| 真实 CUDA v0.17 world parity | 未完成 |
| 多 seed 完整相位因果矩阵 | 未运行 |
| 成本知识传播的长期文化谱系验证 | 未运行 |
| 潜坐标/路由器局部学习 | 未实现 |
| 持久 device-resident latent arena | 未实现 |
| 完整通用主体图数据库与任意嵌套主体 | 未实现 |

## 三 seed 1500-tick 输入结论

用户提供的三个亲和异质环境运行在 tick 1500 时表现出较高一致性：

- alive：`1337–1381`；
- effective founder lineages：`17.33–22.32`；
- strategy effective dimensions：`15.74–20.06`；
- action entropy：`1.724–1.750`；
- boundary cohesion：`0.379–0.418`。

相较旧环境长跑，环境多元化明显延缓了功能策略维度压缩，但没有证明永久维持开放式多样性。

原始窗口相关在三个 seed 中重复显示：

- mortality 与同/下一窗口 cohesion 为正；
- effective lineages 与 cohesion 为强负；
- largest-lineage fraction 与 cohesion 为正；
- strategy dimensions 与 action entropy 为强正；
- lineage-group pair enrichment 与 cohesion 未形成稳定正关系。

这些结果不支持直接把高凝聚解释为“多世系对抗锁定”。raw correlation 可能被 tick、人口周期和共同趋势主导。

## v0.17 当前方向

v0.17 暂停继续增加认知层或环境通道，转为两个工作流：

1. `multi-seed-long-run-analysis-v2`
   - first differences；
   - 控制 tick/alive 的 partial correlations；
   - mortality→cohesion 的 ±3 窗口 cross-lag；
   - 每 1000 tick 趋势斜率；
   - 跨 seed 同方向计数；
   - 无知识传播时的文化谱系解释警告。

2. `phase-checkpoint-counterfactual-plan-v1`
   - 从完整人口周期选择 rise/peak/decline/trough；
   - 映射到可信 `.sechk`；
   - 同 checkpoint、同 keyed randomness 分支；
   - 分别中和亲和、消融记忆、旁路选择、关闭知识 residual、关闭未来知识传播。

## 新科学干预边界

- `neutralize-resource-affinity`：只把有效亲和设为均匀固定预算，不修改基因、遗传或环境；
- `disable-knowledge-policy`：停止知识 residual 发布，保留知识学习、副本和成本；
- `disable-knowledge-transfer`：停止未来副本传播，保留已有副本；
- 原有 `ablate-working-memory` 与 `bypass-sparse-selection` 继续使用。

所有开关进入 clone 和 full checkpoint。旧 checkpoint 缺失字段时按关闭恢复。

## 验证

- 88 tests：87 passed，1 个真实 CUDA 测试因无设备跳过；
- v0.16/v0.17 30-tick 无干预兼容：
  - 266 个共同非计时 metrics 字段一致；
  - 98 个 evolution-progress 字段一致；
  - 六类知识/路由/记忆日志共同字段一致；
  - tick 15/30 的 38 个 checkpoint 数组 bitwise identical；
- 用户 seed10001 3000-tick 报告可识别完整末期周期：rise 2520、peak 2610、decline 2730、trough 2790；
- 60-tick 单调 smoke 没有完整周期，执行器会拒绝正式 phase claim，只有显式 `--allow-incomplete-cycle` 才可用于管线测试；
- 三 seed 60-tick基础设施 smoke 已生成 v2 分析；
- 真实 CUDA v0.17 尚未验证。

## 下一步优先级

1. 对三个 1500-tick run 的原始目录执行 v0.17 analyzer，比较 raw、difference、partial 与 cross-lag；
2. 从三个 seed 的完整 `.sechk` 在相同生态相位执行至少 60–120 tick 干预矩阵；
3. 新增 costed-transfer long-run 对照，确认知识根谱系是否能跨遗传世系传播；
4. 对亲和性状分别计算 phase-specific 生存和成功亲本选择差；
5. 完成真实 CUDA v0.17 parity；
6. 只有因果矩阵显示环境轴仍不足时，再考虑移动危险源或局部生态工程。

暂不采用：按谱系奖励、强制多样性、提高跨组惩罚、简单提高 mutation rate、全局类别 embedding、更深网络或用 fallback phase 标签作科学结论。
