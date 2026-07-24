# Subject Evolution 项目状态（v0.14.0）

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
| v0.13 量化短期工作记忆 | 完成 |
| v0.13 稀疏 Query-Key stable Top-k 临时工作集 | 完成 |
| v0.14 Top-k 实体级离散遗传容量 | **完成** |
| v0.14 工作记忆与选择器 checkpoint 因果消融 | **完成** |
| 真实 CUDA v0.14 world parity | 未完成 |
| 潜坐标/路由器局部学习 | 未实现 |
| 持久 device-resident latent arena | 未实现 |
| 完整主体图数据库与任意嵌套主体 | 未实现 |
| 完整主体性评分 | 未实现 |

## v0.14.0 设计边界

Top-k 不再必须是全局配置常量。新 schema `inherited-discrete-topk-v1` 为每个实体增加一个遗传容量性状，并将其稳定映射到离散等级，例如 `0/1/2/4/8`。

该性状只决定每 tick 最多有多少匹配知识副本进入临时 L2 工作集。它不定义类别语义，也不改变权威知识容量、复制、损坏、验证或内容谱系。更大的 K 通过现有候选扫描、选中副本、潜维度和 MAC 账本自然承担更高计算成本。

新增两个 scientific checkpoint intervention：

- `ablate-working-memory`：清零并冻结工作记忆；
- `bypass-sparse-selection`：绕过临时 Top-k，但保留全部知识副本并继续执行 L2。

两者均不直接替换动作。

## 兼容性

固定 K schema 下，v0.13 与 v0.14：

- 231 个共同非计时 metrics 字段一致；
- outcome、policy contribution、routing cost、selection 共同字段逐行一致；
- tick 15/30 的 37 个共同 checkpoint 数组一致。

## 短验证

- 64 tests：63 passed，1 个真实 CUDA 测试因无设备跳过；
- 遗传容量条件双重复：235 个共同非计时字段、核心日志和 37 个 checkpoint 数组全部一致；
- 遗传容量相对固定 K=4，在单 seed 30-tick 场景中减少约 41.44% L2 MAC 和 28.44% 路由能耗；
- checkpoint 因果分支证明工作记忆和 Top-k 选择均会改变后续世界轨迹，但不构成适应优势结论。

## 下一步建议

1. 在真实 GPU 上验证遗传容量解析、stable Top-k、L2 residual、成本预算和完整世界状态；
2. 做多 seed、多 intervention tick 的 memory/selection 消融，避免单轨迹误判；
3. 加入单内容/单谱系消融，但必须保持副本谱系与成本账本可恢复；
4. 评估容量性状在更长但受控的实验中是否发生选择，而不是仅观察初始随机分布；
5. 暂不引入全局类别 embedding、固定权威槽位或普通 float Softmax Attention。
