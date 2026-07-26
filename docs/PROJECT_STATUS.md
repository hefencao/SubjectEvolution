# Subject Evolution 项目状态

版本：**0.27.0**

## 本轮输入与结论

用户提供的 `analyses.zip` 包含三组已完成的 v0.26 后续实验：crowding 共同边界复跑、scarcity/mortality 事件复制，以及 crowding 剩余知识机制消融。三组 execution preflight 均通过，结果可与最初 crowding 结果按同一 manifest SHA-256 合并。

综合四份签名结果后，共覆盖 18 个自然事件锚点和 72/108 个 eligible anchor–intervention pairs。当前最稳健的机制近端结果是：关闭未来知识传播后，区域 active transferred roots 在 crowding、mortality、scarcity 三类事件的三个 seed 中均下降，seed-level 均值分别为 `-84.33`、`-50.50`、`-36.33`。这支持“传播在短 horizon 内维持局部文化状态”，不等于传播提高人口、适应度或主体性。

`freeze-group-refresh` 对 current-label cohesion 的负向方向在三类事件中重复，但 checkpoint-common cohesion 没有跨 seed 稳定方向。原先的大幅 cohesion 下降主要来自评价分区随干预改变，不能解释为群组刷新提高了共同边界内部利益流。

区域 alive 仍混合留存、迁移、死亡和事件后出生。因此 v0.27 不增加新世界机制，而是新增 stable-ID event cohort 终点分解，并把多结果综合、缺口识别和后续签名计划提升为正式工具。

## v0.27 新增能力

### Event cohort endpoint decomposition

每个 anchor 在 event tick 冻结全局与目标区域的 alive stable entity IDs，在各分支自己的 horizon 终点精确分解：

- 事件 cohort 留在原区域；
- 事件 cohort 存活但位于区域外；
- 事件 cohort 在终点缺失；
- 事件时已存在、随后迁入目标区域的实体；
- 事件后出生且终点位于目标区域的实体。

恒等式为：

```text
Δ regional alive
= existing in-migrants
+ post-event-born-at-final
- event-cohort survived outside
- event-cohort absent
```

每个 anchor/branch 的残差必须为 0。该状态是 run-local 诊断，不写入 checkpoint，不影响策略、行动、空间、关系、群组、知识、出生死亡或环境提交。

### Results v4 与 execution plan v3

- execution plan：`natural-event-execution-plan-v3`；
- trajectory marker：`natural-event-trajectory-run-v3`；
- paired results：`natural-event-paired-intervention-results-v4`；
- aggregation：`natural-event-paired-delta-aggregation-v3`；
- cohort schema：`event-region-endpoint-cohort-decomposition-v1`。

v0.27 兼容读取 plan v1/v2 和 results v2/v3。启用 cohort audit 时，旧 marker 不会被静默当作 v3 轨迹复用。

### 跨结果综合

`subject_evolution.natural_event_result_synthesis`：

- 验证所有结果共享同一 manifest hash；
- 按 `(anchor_id, intervention)` 合并；
- 重复结果必须在核心世界结果上兼容；
- 优先采用 cohort、共同边界等诊断更完整的重复分支；
- 重新执行先 seed 内平均、再跨 seed 汇总；
- 计算 manifest pair coverage 与逐事件/干预诊断覆盖；
- 只将跨事件、跨 seed 重复方向登记为描述性复制；
- 生成新的 v3 签名执行计划。

## 当前实现矩阵

| 领域 | 状态 | 边界 |
|---|---|---|
| CPU reference | 完成 | 当前科学语义权威 |
| GPU strict-reference | 完成 | 验证设备，执行 reference 世界 |
| GPU hybrid-accelerated | 部分完成 | 长程 parity 未证明 |
| 四资源异步生态位 | 完成 | 任意信息通道 schema 未完成 |
| 环境插件 ABI | 完成 | 非负标量场、默认关闭、无实体访问 |
| 实体/生命周期/谱系 | 完成 | 主要提交仍在 CPU |
| 遗传策略与 K1–K4 知识 | 完成 | 固定行动/特征 vocabulary 仍是模型约束 |
| L1/L2、路由成本、记忆、Top-k | 完成 | 均可 checkpoint 与消融 |
| 社会关系与 adaptive groups | 完成 | 候选主体结构，不是主体性判定 |
| natural-event manifest / execution | v0.24–v0.25 完成 | 暴露盲选、哈希预检、共享轨迹 |
| checkpoint-common boundary | v0.26 完成 | 只修正评价口径 |
| result audit / synthesis | **v0.27 完成** | 不重选锚点、不升级因果结论 |
| event cohort endpoint audit | **v0.27 完成** | 终点身份分解，不是完整路径流量账本 |
| 任意嵌套主体数据库 | 未完成 | 当前是候选图与摘要 |
| 主体性/主体偏移评分 | 未完成 | 不允许由单一代理推出 |
| Hero RL、多 GPU | 未完成 | 当前非科学优先级 |

## 当前实验覆盖

| 批次 | Anchors | 已执行 pairs | 主要用途 |
|---|---:|---:|---|
| 初始 crowding | 6 | 18 | transfer / group refresh / affinity |
| common-boundary rerun | 6 | 6 | group refresh 测量解耦 |
| mortality + scarcity replication | 12 | 36 | 三个主要机制跨事件复制 |
| crowding knowledge ablation | 6 | 18 | policy / memory / Top-k |
| 综合去重后 | 18 | 72 | manifest eligible 总数为 108 |

尚缺的 36 pairs 是 mortality/scarcity × `disable-knowledge-policy`、`ablate-working-memory`、`bypass-sparse-selection`。现有所有结果均缺 event cohort，因此 demographic 解释仍应等待 v0.27 cohort 复跑。

## 验证

- 全量测试：`131 passed, 1 skipped`，见 `docs/v0.27/FINAL_TEST_REPORT.txt`；
- v0.26→v0.27 默认 CPU 20 tick：1573 个共同非计时 metrics 单元零差异；
- `evolution_progress.jsonl` byte-identical；
- v0.26 tick-10 `.sechk` 由 v0.27 恢复到 tick 20，与连续 v0.27 semantic state 一致；
- event cohort 恒等式、stable-ID 槽位复用、独立 anchor horizon 和结果综合均有测试覆盖；
- 默认世界轨迹不因诊断层新增而改变。

## 下一阶段执行顺序

1. 运行 `primary_event_cohort_rerun_execution_plan.json`，先分解三个主要机制的区域人口终点；
2. 运行 `crowding_knowledge_cohort_rerun_execution_plan.json`，补足 crowding 知识机制的人口构成；
3. 运行 `remaining_event_knowledge_cohort_rerun_execution_plan.json`，完成 108/108 机制覆盖；
4. 综合 v4 结果后，再决定是否需要路径级 cohort flow ledger 或更长 horizon；
5. 不因现有结果调整基础收益、群组奖励、传播概率或资源亲和参数；
6. 真实 CUDA hybrid parity 继续独立推进，不与机制结论混合。
