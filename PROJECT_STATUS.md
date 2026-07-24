# Subject Evolution 项目状态（v0.7.0）

## 当前完成阶段

| 功能 | 状态 |
|---|---|
| 动态知识副本、容量、维持与损坏 | K1 已完成 |
| 有代价知识交换与传播谱系 | K1 已完成 |
| 局部五维后果记录与经验更新 | K2 已完成 |
| 知识稀疏残差进入策略 | **K3 已完成** |
| 知识内容进入候选主体图 | 未实现，K4 |
| 完整设备驻留世界循环 | 未实现 |
| 完整主体图数据库及任意嵌套主体 | 未实现 |
| checkpoint 全世界恢复与离线反事实重放 | 未实现 |
| 信息模板寄生主体 | 未实现 |
| 完整主体性评分 | 未实现 |
| Hero 强化学习 | 未实现 |
| 任意信息通道 schema | 未实现 |

## K3 概要

v0.7.0 实现 `dynamic-knowledge-k3-v1` 和 `inherited-linear-policy-knowledge-residual-v1`。策略关系为遗传先验 logits 加本地知识副本形成的稀疏 residual。K3 新增五个 outcome preference 性状和一个 knowledge-use-strength 性状，但旧 128 个遗传策略权重的含义与位置保持不变。

K1/K2 配置仍使用 136 维基因组；K3 配置使用 142 维。K2 模式与 v0.6.5 的 141 个共同非计时指标、tick 10/20 的 32 个共同 checkpoint 数组及知识日志完全一致。

K3 输出分别记录 genetic logits、knowledge residual、genetic-only action 和 combined action。知识不绕过既有控制/结算边界，也不使用全局奖励、未来信息或反向传播。

## 短周期验证

本轮遵循短迭代策略，仅运行 30 ticks 三条件双重复：K2 control、K3 private、K3 costed exchange。全部非计时 metrics、日志和 checkpoint 确定性检查通过。完整测试为 31 passed、1 skipped；skip 项是当前容器无 CUDA 的真实 GPU 测试。

短运行只证明实现和确定性，不构成长期适应、选择效应或主体性结论。

## CPU/GPU 状态

用户已确认 v0.6.4/v0.6.5 的 K2 hybrid 路径在 `mvp_short_k2_exchange` 运行至 tick 1000 未发现 CPU/GPU 偏差，并确认周期位置修复后无问题。K3 GPU 路径采用稀疏 residual 上传，但当前容器无 CUDA，尚需在真实 GPU 上做新的 K3 逐阶段 parity 验证；在完成前不能把 K3 hybrid 结果视为硬件一致性已证明。

## 下一阶段建议

下一阶段是 K4：将具有复制谱系、变体和承载体分布的知识内容作为候选主体图节点，评估持续性、宿主成本、复制优势和利益边界。K4 不应扩展为 Hero RL 或任意嵌套主体数据库的全部实现，应继续采用短周期、小世界和对照实验推进。
