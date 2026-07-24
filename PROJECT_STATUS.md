# Subject Evolution 项目状态（v0.13.0）

## 已完成阶段

| 功能 | 状态 |
|---|---|
| K1 动态知识副本、容量、成本、交换与损坏 | 完成 |
| K2 局部五维后果学习 | 完成 |
| K3 知识 residual 接入公开策略 | 完成 |
| K4 内容谱系与候选主体图诊断 | 完成 |
| v0.9 全世界 checkpoint 恢复与离线反事实分支 | 完成 |
| v0.10 L1 可变长度潜知识与量化线性路由 | 完成 |
| v0.11 L2 遗传量化两层 MLP 路由 | 完成 |
| v0.12 路由计算成本与能量预算仲裁 | 完成 |
| v0.13 量化短期工作记忆 | **完成** |
| v0.13 稀疏 Query-Key stable Top-k 临时工作集 | **完成** |
| 真实 CUDA v0.13 world parity | 未完成 |
| K 的实体级遗传/可塑调节 | 未实现 |
| 潜坐标/路由器局部学习 | 未实现 |
| 持久 device-resident latent arena | 未实现 |
| 完整主体图数据库与任意嵌套主体 | 未实现 |
| 完整主体性评分 | 未实现 |

## v0.13.0 设计边界

本版本吸收“工作记忆”和“状态相关知识选择”，但没有采用固定 `K_max` 权威槽位、全局 Category Embedding 或 float Softmax Attention。

权威知识仍是可变长度动态 SoA。Top-k 只产生每 tick 可重建的临时工作集，不改变宿主容量、复制、损坏或内容谱系。Query/Key 来自宿主状态、量化工作记忆、内容自身 latent、局部五维后果与可靠性，参数来自遗传基因。

Working Memory 是每实体 4D `int16` 状态，使用上 tick 的 prediction error 与公开观察变化进行定点更新。更新发生在本 tick 后果提交后，仅影响下一 tick。

## 兼容性

模块关闭时，v0.12 与 v0.13：

- 204 个共同非计时 metrics 字段一致；
- outcome、policy contribution、routing cost 共同列逐行一致；
- knowledge/evolution JSONL byte-identical；
- tick 15/30 的 35 个共同 checkpoint 数组一致。

## 验证

- 62 tests：61 passed，1 个真实 CUDA 测试因无设备跳过；
- 五条件各同 seed 双重复；
- 230 个非计时字段、核心日志及 checkpoint 全部复现；
- Top-k=2 在短场景相对 memory-only 降低约 52.74% L2 MAC；Top-k=4 降低约 17.62%；Top-k=8 选中全部候选，无计算收益。

## 下一步建议

1. 在真实 GPU 上验证 memory、selection plan、L2 residual、cost budget 与完整世界状态；
2. 将 K 从配置常量升级为有成本的实体级遗传性状，但必须保持稳定 tie 和容量独立；
3. 使用 full checkpoint 做 memory-only、selection-only、单内容删除和 K sweep 反事实；
4. 多 seed、预算匹配后再判断时间记忆和稀疏选择是否产生长期适应价值；
5. 暂不引入全局类别 embedding 或普通 Softmax Attention。
