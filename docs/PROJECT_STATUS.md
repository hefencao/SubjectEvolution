# Subject Evolution 项目状态

版本：**0.28.0**

## 本轮输入与结论

用户提供的 `analyses.zip` 包含：

- 已完成的 18-anchor primary cohort rerun（54 pairs）；
- 已完成的 6-anchor crowding knowledge cohort rerun（18 pairs）；
- 已通过 preflight、但未附 results 的 12-anchor mortality/scarcity knowledge plan（36 pairs）。

因此当前实际结果覆盖仍为 **72/108 eligible pairs**。

v0.27 stable-ID endpoint 恒等式本身成立，但本轮审计发现更上游的执行时序问题：所有 72 个干预都在 prior checkpoint tick 应用，比名义 event tick 提前 30 或 60 ticks。48/72 pairs 在 event tick 的区域 alive 数已经与 baseline 不同；旧 cohort schema 也没有实体集合哈希，人数相同的 pairs 仍无法证明身份相同。

旧结果估计的是 checkpoint 后整段总效应，而不是共同自然事件状态形成后的 post-event 机制效应。v0.28 因此不增加世界机制，而是新增 shared-prefix/event-checkpoint 执行边界。

## v0.28 新增能力

### Event-timed paired execution

`subject_evolution.natural_event_timed_execution`：

1. 按 `(source checkpoint SHA-256, event tick)` 只演进一次共同前史；
2. 保存并验证 event checkpoint file/state SHA-256；
3. baseline 与 interventions 从完全相同的 event checkpoint 开始；
4. 在干预前冻结共同群组边界和 event cohort；
5. 干预严格在名义 event tick 应用；
6. 每个 pair 输出 `shared-event-checkpoint-pairing-v1`。

### Event cohort v2

`event-region-endpoint-cohort-decomposition-v2` 在 v1 五类终点分解基础上新增：

- `event_global_ids_sha256`；
- `event_region_ids_sha256`。

pairing 只有在 event alive、全局 identity hash、区域 identity hash 全部一致时有效。

### 两类估计量显式分离

| 入口 | Timing | 解释 |
|---|---|---|
| `natural_event_execution` | `checkpoint-immediate-v1` | prior checkpoint 后机制总效应，可改变事件形成 |
| `natural_event_timed_execution` | `anchor-event-tick-v1` | 共同事件状态形成后的短 horizon 机制效应 |

result synthesis v2 拒绝将两类结果池化。

### 新签名计划

| 计划 | Anchors | Shared prefixes | Post-event trajectories |
|---|---:|---:|---:|
| event-timed primary | 18 | 18 | 72 |
| event-timed crowding knowledge | 6 | 6 | 24 |
| event-timed mortality/scarcity knowledge | 12 | 12 | 48 |

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
| 暴露盲选 manifest | 完成 | 不读取事后 outcome |
| checkpoint-immediate execution | v0.25–v0.28 保留 | pre-event 总效应估计量 |
| common boundary / endpoint cohort | v0.26–v0.28 完成 | 诊断层，不反馈世界 |
| event-timed execution | **v0.28 完成** | shared event state + stable-ID hash proof |
| result synthesis | **v0.28 v2** | timing estimand 不可混合 |
| 任意嵌套主体数据库 | 未完成 | 当前是候选图与摘要 |
| 主体性/主体偏移评分 | 未完成 | 不允许由单一代理推出 |
| Hero RL、多 GPU | 未完成 | 当前非科学优先级 |

## 当前科学解释

1. checkpoint-immediate transfer-off 在三类事件中均减少局部文化根，仍可描述为“提前关闭传播后，后续局部文化状态减少”。
2. 不能把这些方向直接写成 event-conditional 机制效应，因为干预已在事件前改变世界。
3. v0.27 cohort 分解可描述每个分支自己的终点构成，但 branch-specific cohorts 不能作为共同 cohort delta。
4. freeze-group-refresh 的 current-label cohesion 下降仍主要受评价边界定义影响。
5. mortality/scarcity 的 policy、memory、Top-k 结果尚未附上，覆盖仍是 72/108。

## 验证

- 全量测试：`133 passed, 1 skipped`；
- event-timed CPU smoke：1 shared prefix、2 post-event trajectories，pairing failure=0，baseline/branch event alive 相同；
- v0.27→v0.28 默认世界兼容测试见 `docs/v0.28/V027_V028_COMPATIBILITY_REPORT.json`；
- v0.27 trusted checkpoint 恢复测试见同一报告；
- event cohort identity hash、不同 event tick 不错误去重、signed plan、prefix/trajectory resume 均有测试覆盖；
- 默认世界轨迹不因新执行层改变。

## 下一阶段执行顺序

1. 运行 `event_timed_primary_execution_plan.json`；
2. 运行 `event_timed_crowding_knowledge_execution_plan.json`；
3. 直接运行 event-timed remaining-event knowledge plan，而不是先执行旧 checkpoint-immediate 缺失计划；
4. 只有 pairing failure=0 的结果才进入 event-conditional synthesis；
5. 不因旧 branch-specific cohort 方向修改传播概率、资源亲和、记忆或群组规则；
6. 真实 CUDA hybrid parity 继续独立推进。
