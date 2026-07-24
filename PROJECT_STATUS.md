# Subject Evolution 项目状态（v0.5.0）

## 本轮完成：K1 动态知识副本与有代价交换基础

本版本实现 `dynamic-knowledge-k1-v1`，并保持现有遗传策略 schema 为
`inherited-linear-policy-v1`。知识在 K1 中不进入策略特征、logits、控制提案或行动
仲裁；它只作为可复制、可遗忘、可损坏且有物理成本的世界内数据存在。

### 已实现

- 后端无关、容量倍增的动态 SoA `KnowledgeCatalog` 与 `KnowledgeArena`；
- 不可变知识内容及 `parent_content_id` 变体谱系；
- 独立 holder copy：副本 ID、持有主体、来源、置信度、样本量、创建/验证 tick、编码字节；
- holder 字节预算及明确的 `oldest-copy-v1` 淘汰规则；
- 每 tick 存储维持成本，无法支付时按同一规则淘汰副本；
- 从已成功结算的 `SIGNAL` 行生成 `KnowledgeTransferPlan`；
- 发送、接收、丢失、误分类损坏、注意力槽、重复内容和容量仲裁；
- 发送者、接收者、来源主体、副本/内容 ID、字节、tick、交付/损坏及提交状态的 CSV 审计；
- `KnowledgeObservationPlan`：按 holder 分段的只读发布快照；K1 尚无策略消费者；
- 知识指标、事件摘要、检查点数组、run metadata 和 scientific validity 元数据；
- `run_manifest.json`、`resolved_config.json`、`scientific_validity.json`；
- `run.validation_mode` 的 entity/free-pool、数值范围、周期位置、死亡群组清理和知识容量不变量；
- 修复同 tick 采集后分享可使最终能量超过 `max_energy` 的提交漏洞；分享金额、关系事件和 action resolution 现在按提交时真实容量重新仲裁。

### K1 对照配置

- `configs/mvp_small_k1_none.json`：无知识；
- `configs/mvp_small_k1_private.json`：私有知识，仅存储/遗忘成本，无交换；
- `configs/mvp_small_k1.json`：正式有代价交换；
- `configs/mvp_small_k1_zero_cost.json`：零成本失效对照。

四条件均已用 seed 10001、CPU、500 ticks 完整运行。零成本交换与无知识条件的共同
非计时 metrics 完全相同，tick 250/500 的 12 个共同世界数组逐数组相同；这验证了
知识数据本身没有暗中改变 `inherited-linear-policy-v1`。

## 仍未实现

- **K2**：行动结算后的局部后果向量记录与副本经验更新；
- **K3**：新的策略 schema、稀疏知识残差及遗传/知识 logits 贡献分解；
- **K4**：知识内容复制谱系进入候选主体图及知识主体性评估；
- 完整设备驻留世界循环；
- 完整主体图数据库和任意嵌套主体；
- checkpoint 恢复与真正的离线反事实分支重放；
- 信息模板寄生主体；
- 完整主体性评分；
- Hero 强化学习；
- 任意信息通道 schema（资源、危险、社会三通道仍固定）。

## 下一阶段建议：K2

1. 在 intent/plan/commit 后记录每个行动承载体的能量、完整性、物质、信息和繁殖机会变化；
2. 使用固定宽度后果向量，不压缩为单一 reward；
3. 仅更新实际经历该上下文—行动的本地副本；
4. 将验证次数、最后验证 tick、置信度更新和验证成本纳入计划与指标；
5. 保持 K2 知识仍不影响行动，先验证后果记录、更新守恒和 checkpoint 重放一致性。
