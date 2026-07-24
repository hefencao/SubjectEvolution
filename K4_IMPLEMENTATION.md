# K4 实现说明：知识谱系与候选主体图诊断（v0.8.0）

## 阶段边界

K4 将 K1–K3 已存在的知识内容、独立副本、交换事件、局部验证和策略影响组织为候选主体图诊断，但不改变世界规则：

- 知识内容没有独立执行器；
- K4 不参与 observation、policy、proposal、intent、resolution 或 commit；
- K4 不把候选节点认定为真实主体；
- 宿主状态关联只是观察性统计，不解释为因果收益；
- 不合成未经验证的单一主体性分数。

启用 K4 要求显式使用 `dynamic-knowledge-k4-v1`，并同时启用 K2 learning 与 K3 policy influence。旧 K1/K2/K3 配置默认关闭候选跟踪。

## 数据结构

新增 `knowledge_subjects.py`，核心对象为：

- `KnowledgeCandidateGraphPlan`：当前更新周期发布的不可变候选图快照；
- `KnowledgeCandidateTracker`：低频、后端无关的累计诊断器。

知识内容使用独立候选 subject ID 命名空间：

```text
candidate_subject_id = 2_000_000_000 + content_id
```

每个内容节点追踪：

- `content_id`、`parent_content_id`、`root_content_id`；
- `variant_depth`、创建 tick、来源主体、context/action；
- first/last seen tick；
- 当前与累计副本数；
- 当前与累计唯一宿主数；
- 当前已验证副本与已验证交换副本；
- 当前群组、谱系与空间区域覆盖；
- 后代变体数量。

内容目录仍保持不可变内容语义；副本 arena 继续保存独立的置信度、样本、验证与损坏状态。内容去重不会抹掉副本的独立生命史。

## 候选图边

`candidate-subject-graph-v1` 输出的边包括：

- `variant_of`：内容变体到父内容；
- `held_by`：知识内容到当前或历史宿主；
- `transferred_to` / 传播归因；
- `cost_attributed_to`：发送、接收、维持和验证成本；
- K3 policy influence 与 changed-action 归因。

边使用聚合计数、金额和最后事件 tick，避免为每个事件构造 Python 对象链。

## 候选诊断分量

K4 不输出单一“主体性真值”，而是分别输出：

1. **persistence**：first/last seen、持续 tick、当前是否仍有副本；
2. **replication**：尝试、成功提交、存活副本、本地验证副本、后代变体；
3. **distribution**：独立宿主、群组、谱系和空间区域覆盖；
4. **host cost**：发送、接收、维持和验证能量；
5. **host outcome association**：持有者与非持有者的能量、完整性、物质、信息和繁殖机会均值差；
6. **policy influence**：K3 residual 事件、改变动作事件和 residual 绝对量；
7. **boundary cohesion**：群组、谱系和区域的 same/cross/unknown 流；
8. **autonomy caution**：知识仍依赖宿主，没有独立执行器。

宿主后果保持五维，不压缩为单一 reward。无有效分母时，边界内聚输出空值并设置 `valid=false`。

## 有效复制语义

K4 区分：

- transmission attempt；
- committed copy；
- 当前 surviving copy；
- locally verified copy；
- verified transferred copy；
- descendant variant；
- 跨宿主持续。

同一内容向同一宿主重复复制可以增加副本事件，但不会增加 `unique_holder_count`，因此不能仅靠重复灌入一个宿主夸大分布指标。

## 利益边界

每次传播分别按群组、谱系和空间区域分类为：

- same；
- cross；
- unknown。

交换规则没有被限制为群内传播。候选层只观察实际发生的内部与跨边界传播，并输出：

```text
cohesion = internal_commits / (internal_commits + cross_commits)
```

unknown 不进入该分母，且分母为零时结果无效。

## 更新时序

候选更新发生在一个 tick 的世界动作、关系/群组和生命周期提交之后，并按照 `candidate_update_period` 低频执行。它只读取：

- 已提交的知识目录与副本；
- 已提交实体、群组、谱系和位置；
- 累计成本；
- K3 已记录的策略影响。

因此 K4 tracking on/off 不改变同一 tick 或后续 tick 的任何决策输入。

## 持久化与输出

新增文件：

- `knowledge_content_lineage.csv`；
- `knowledge_subject_candidates.csv`；
- `knowledge_subject_edges.csv`；
- `knowledge_boundary_flows.csv`；
- `knowledge_candidate_summary.json`。

checkpoint 新增 20 个候选诊断数组，保存根内容、变体深度、first/last seen、传播流、成本和策略影响累计量。clone/paired 分支复制候选 tracker 状态，但各分支写入独立输出目录。

## 科学有效性声明

run manifest 与 `scientific_validity.json` 明确记录：

- K4 是 diagnostic-only；
- 不声称主体性真值；
- 宿主后果关联不是因果估计；
- 没有独立 actuator。

## 未包含

K4 不实现：

- 完整通用主体图数据库；
- 任意嵌套主体的控制和生命周期；
- 完整主体性评分；
- 信息模板寄生主体；
- Hero 强化学习；
- 离线反事实 checkpoint 重放；
- 任意信息通道 schema；
- 完整设备驻留世界循环。
