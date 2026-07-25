# Subject Evolution 项目状态

版本：**0.24.0**

## 本轮输入与结论

用户完成旗舰 mortality-trace + adaptive-groups + costed-transfer 配置的三个 seed、1500 tick 运行。三个终点人口为 1360、1352、1328；有效遗传世系为 15.777、21.073、21.303；传播提交为 12,166、12,460、14,168；有效 transferred roots 为 2,011.22、2,051.12、2,183.63。

跨 seed 的局部方向更适合下一轮因果设计：稀缺与新 transferred roots 正相关，但与净建立负相关；拥挤与 outgoing transfer 正相关、与下一窗口凝聚度负相关；死亡压力与 incoming transfer 和下一窗口凝聚度呈弱正方向。观察性事件窗口仍可能由共享原因驱动，不能直接解释为因果。

因此 v0.24 没有继续修改生态规则，而是增加**暴露盲选的自然事件 paired-intervention matrix**，将后续工作转向相同 checkpoint、相同随机流下的机制消融。

## v0.24 新增能力

### 自然事件矩阵

`subject_evolution.natural_event_matrix`：

- 跨多个 seed run 自动发现局部稀缺、拥挤和死亡压力峰值；
- 选择阶段只读取 exposure、区域 alive、tick 与 checkpoint 可用性；
- 明确排除凝聚度、文化根、传播流、谱系和动作熵等结果字段；
- 每个 anchor 记录 progress、resolved config、checkpoint 与总计划 SHA-256；
- 分析 JSON 只作为 rationale/audit，不参与锚点选择；
- 可生成 manifest，也可在审核后执行 baseline 与 eligible interventions；
- 所有分支从同一事件前 checkpoint 出发并保留 keyed randomness。

### 群组刷新消融

新增科学干预：

```text
freeze-group-refresh
```

它不改写现有标签，不重置关系，也不增加控制器；只阻止 branch point 后的群组重新识别。死亡成员仍被清除，新生体保持未分组。状态可 checkpoint、恢复和 clone。

### 文档结构

- 根目录：稳定入口 `README.md`；
- `docs/`：`PROJECT_STATUS.md`、`SCIENTIFIC_ISSUES.md`、`CHANGELOG.md`、`ARCHITECTURE.md`；
- `docs/v0.24/`：本版本实现、输入分析、验证和兼容报告；
- `docs/archive/pre-v0.24/`：旧根目录报告和旧 docs 原样归档。

## 当前实现矩阵

| 领域 | 当前状态 | 边界 |
|---|---|---|
| 配置与 schema | 完成 | 旧 schema 显式兼容，不静默改义 |
| CPU reference | 完成 | 当前科学语义权威 |
| GPU strict-reference | 完成 | 验证设备，但执行 CPU reference 世界 |
| GPU hybrid-accelerated | 部分完成 | 长程 parity 未证明 |
| 四资源异步生态位 | 完成 | 固定四通道，任意通道 schema 未完成 |
| 环境过程插件 ABI | 完成 | 只能返回非负标量场增量，默认关闭 |
| 实体、谱系、出生死亡 | 完成 | 提交仍主要在 CPU |
| 遗传策略 | 完成 | 8 actions × 16 features 的固定架构 |
| 社会关系与候选群组 | 完成 | 候选结构，不是主体存在结论 |
| adaptive group refresh | 完成 | v0.24 新增 freeze 消融 |
| K1–K4 动态知识 | 完成 | 内容、承载副本、主体分离 |
| 有代价知识传播 | 完成 | 已出现跨谱系和跨群组传播 |
| 潜知识 L1/L2 | 完成 | 可变长度、量化 residual |
| 路由计算成本 | 完成 | entity-scoped 预算与归因 |
| 工作记忆 | 完成 | 定点状态、可遗传参数、可消融 |
| 遗传 Top-k | 完成 | 临时选择，不是权威存储 |
| 资源亲和 | 完成 | 固定预算四资源表型，可中和 |
| mortality trace | 完成 | 局部死亡形成环境证据，不是生物危险源 |
| danger evidence mixture | 完成但旗舰基线关闭 | 当前三 seed 不能评价其适应价值 |
| checkpoint/replay | 完成 | `.sechk` 仅加载可信来源 |
| phase counterfactual | 完成 | 相位选择观察性 |
| local event counterfactual | 完成 | 单 run 事件分支 |
| natural-event matrix | **v0.24 完成** | 多 seed、暴露盲选、哈希预注册 |
| 长期分析 | v7 完成 | 相关和事件研究不等于因果 |
| 任意嵌套主体数据库 | 未完成 | 当前是候选图和低频摘要 |
| 主体性评分 | 未完成 | 不允许由单一代理指标推出 |
| Hero RL | 未完成 | 不进入当前科学优先级 |
| 多 GPU | 未完成 | 暂不优先 |

## 验证状态

- 全量测试：`120 passed, 1 skipped`；
- 跳过项：真实 CUDA/CuPy 设备测试；
- v0.23 与 v0.24 默认路径：20 tick、341 个共同 metrics 字段中，排除 13 个计时字段后零差异；
- `knowledge_events.jsonl` byte-identical；
- v0.24 可读取 v0.23 完整 checkpoint，并在 tick 20 得到与连续 v0.24 相同的共同非计时 summary；
- `freeze-group-refresh` 的状态、skip 计数和 checkpoint 恢复已测试；
- manifest checksum、分析只读角色、暴露盲选及干预 eligibility 已测试。

## 下一阶段优先级

1. 在用户现有三个 seed 的原始 run 目录上生成 v0.24 manifest；
2. 审核锚点后执行 transfer、knowledge-policy、working-memory、Top-k、resource-affinity 与 group-refresh 矩阵；
3. danger evidence 在当前基线为 disabled，应自动标记不可识别，不应强行执行；
4. 比较 scarcity、crowding、mortality 三类事件中 transferred-root 建立、留存、跨区域扩散与局部人口结果；
5. 只有配对分支显示现有观察轴不足时，才考虑新增非生物环境过程；
6. 独立推进真实 CUDA hybrid parity，不与科学机制修改混合。

继续暂不采用：按谱系/群组奖励、自动保护多样性、提高跨组惩罚、单纯提高 mutation rate、全局类别 embedding、普通 Softmax attention、环境层第二套生物实体，以及将观察性群组指标直接命名为主体性。
