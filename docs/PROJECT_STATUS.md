# Subject Evolution 项目状态

版本：**0.26.0**

## 本轮输入与结论边界

用户提供的 execution result 完整覆盖其选定计划：3 seeds、6 个 crowding anchors、3 个干预，共 16 条实际共享轨迹，8 条 branch 被去重。preflight 显示 10 个 checkpoint/progress/config 文件检查全部通过，`execution_ready=true` 且 `full_audit_ready=true`。

当前可支持的最强结论是：关闭未来知识传播后，三个 seed 的区域 active transferred roots 均下降，seed-level 平均 `-84.33`，说明传播在 crowding 事件后的短 horizon 内维持局部文化状态。人口与 current-label cohesion 未形成可解释的稳健收益结论。

`freeze-group-refresh` 的原 cohesion 在三个 seed 均下降，平均 `-0.2103`，但该指标使用的群组标签正是干预对象，因此存在测量耦合。v0.26 先修正评价边界，不把该方向直接解释成社会凝聚机制。

中和资源亲和后 crowded-region alive 在三个 seed 均增加，平均 `+7.33`；但区域 alive 混合存活、出生、死亡和迁移，当前仅列为跨事件复制优先项。

## v0.26 新增能力

### Checkpoint-common boundary

natural-event trajectory 从同一 checkpoint、应用干预前冻结稳定实体 ID 与群组 token。后续分享流同时按当前分支标签和共同冻结标签记账，新增 reference cohesion 与 boundary-definition gap。该状态只存在于诊断层，不反馈世界。

### Results v3 与 outcome audit

- execution plan：`natural-event-execution-plan-v2`；
- trajectory marker：`natural-event-trajectory-run-v2`；
- paired results：`natural-event-paired-intervention-results-v3`；
- aggregation：`natural-event-paired-delta-aggregation-v2`；
- outcome audit：`natural-event-outcome-audit-v1`。

v0.26 兼容读取 v0.25 plan v1 与 results v2。旧轨迹若缺少共同边界字段，不会被当作 v0.26 common-boundary trajectory 复用。

### Result audit 与后续计划

`subject_evolution.natural_event_result_audit` 验证 result/plan/manifest 哈希链，分类指标解释层级，并根据实际覆盖生成：

| 批次 | Anchors | Shared trajectories | 用途 |
|---|---:|---:|---|
| common-boundary rerun | 6 | 8 | 重新评价 freeze-group-refresh |
| remaining event replication | 12 | 48 | scarcity/mortality × 当前三个机制 |
| remaining mechanism ablation | 6 | 16 | crowding × policy/memory/Top-k |

## 当前实现矩阵

| 领域 | 状态 | 边界 |
|---|---|---|
| CPU reference | 完成 | 当前科学语义权威 |
| GPU strict-reference | 完成 | 验证设备，执行 reference 世界 |
| GPU hybrid-accelerated | 部分完成 | 长程 parity 未证明 |
| 四资源异步生态位 | 完成 | 任意信息通道 schema 未完成 |
| 环境插件 ABI | 完成 | 非负标量场、默认关闭、无实体访问 |
| 实体/生命周期/谱系 | 完成 | 主要提交仍在 CPU |
| 遗传策略 | 完成 | 固定 8 actions × 16 features |
| 社会关系与 adaptive groups | 完成 | 候选主体结构；可 freeze 消融 |
| K1–K4 动态知识 | 完成 | 内容、承载副本、主体分离 |
| 有代价传播与局部文化诊断 | 完成 | 传播存在不等于适应性 |
| L1/L2、路由成本、工作记忆、Top-k | 完成 | 均可 checkpoint 与消融 |
| 资源亲和、mortality trace | 完成 | 适应价值仍需 paired branches |
| natural-event manifest planner | v0.24 完成 | 暴露盲选、哈希预注册 |
| manifest execution runtime | v0.25 完成 | 路径映射、预检、去重、续跑 |
| common-boundary paired evaluation | **v0.26 完成** | 只改变诊断口径，不改变世界 |
| result audit / follow-up planner | **v0.26 完成** | 不重选锚点、不自动执行 |
| 固定 checkpoint cohort/retention | 未完成 | 区域 alive 仍受迁移构成影响 |
| 任意嵌套主体数据库 | 未完成 | 当前是候选图与摘要 |
| 主体性/主体偏移评分 | 未完成 | 不允许由单一代理推出 |
| Hero RL、多 GPU | 未完成 | 当前非科学优先级 |

## 验证

- 全量测试：`126 passed, 1 skipped`；
- v0.25→v0.26 默认 CPU 20 tick：1570 个共同非计时 metrics 单元零差异；
- `evolution_progress.jsonl` 与 7 类知识日志逐字节一致；
- v0.25 tick-10 `.sechk` 由 v0.26 恢复到 tick 20，内部 simulation state 与连续 v0.26 零差异；
- common-boundary 实际 checkpoint 集成测试通过；
- 旧 execution plan v1 与 results v2 可由 v0.26 审计。

## 下一阶段执行顺序

1. 先运行 `docs/v0.26/common_boundary_rerun_execution_plan.json`；
2. 共同边界结果出来后，只用 `post_event_reference_cohesion_region` 评价 freeze-group-refresh；
3. 再运行 scarcity/mortality 复制，检查 transfer 文化维持与 affinity regional alive 方向是否跨事件保持；
4. 增加 checkpoint-fixed cohort survival/retention，拆分区域人口变化中的迁移成分；
5. 最后补齐 knowledge policy、working memory、Top-k 三项 crowding 消融；
6. 真实 CUDA hybrid parity 继续独立推进，不与机制结论混合。

继续不采用：按谱系/群组奖励、自动保护多样性、提高跨组惩罚、单纯提高 mutation rate、环境层第二套生物实体，以及将观察性群组指标直接命名为主体性。
