# Subject Evolution 项目状态

版本：**0.30.0**

## 当前主线

项目主线已从自然事件执行工具转向：

1. **主体结构**：候选社会结构的持续、分裂、合并、消散和复现；
2. **多元环境**：多尺度资源组合、危险、死亡痕迹、环境周转及主体暴露分化；
3. **结构—环境耦合**：只做观察性测量与可审计实验设计，不把关联升级为主体性或环境因果结论。

v0.29 的 group label、region partition、anchor selection 与 event-timed 工作流继续保留，作为已完成的测量与实验基础。

## v0.30 新增能力

### Candidate-subject succession

- schema：`stable-membership-subject-succession-v1`；
- 每次实际 group refresh 后按 stable entity ID 比较成员集合；
- 记录 formation、dissolution、split、merge、reactivation；
- 记录 same-token、exact-membership、member-weighted Jaccard 和 inheritance；
- stable ID 防止槽位复用伪造主体连续性；
- succession edge 不进入世界主体图，不反馈世界。

### Multiscale subject–environment atlas

- schema：`multiscale-subject-environment-atlas-v1`；
- signature：四资源容量归一化均值 + hazard + mortality trace；
- 支持多个 `normalized-fixed-count-grid-v1` scale；
- 当前主线配置使用 `2×2`、`4×4`、`8×8`；
- 记录环境有效维数、区域距离、资源空间 CV、时间周转和实体区域有效数；
- 记录 lineage/social exposure association、covered fraction 和 region span；
- association 仅包含至少两个成员的 label，排除 social token 0。

### Offline synthesis

- 新增 `multi-seed-subject-environment-analysis-v1`；
- 将每个 atlas evaluation 对齐到此前最近一次 group refresh；
- 报告环境周转与主体继承、split/merge、social association/span 的观察性相关；
- 先逐 run/seed 分析，再登记至少三个 seed 同号方向。

### Protocol and long-run schemas

- protocol audit：`structural-measurement-protocol-audit-v2`；
- long-run analysis：`multi-seed-long-run-analysis-v9`；
- run manifest 与 run metadata 发布主体 succession 和 atlas provenance；
- full checkpoint、clone 和 trusted replay 保存诊断 accounting state。

## 当前实现矩阵

| 领域 | 状态 | 当前边界 |
|---|---|---|
| CPU reference | 完成 | 科学语义权威 |
| GPU strict-reference | 完成 | 验证设备，世界仍使用 reference 语义 |
| GPU hybrid-accelerated | 部分 | 多 tick parity 未证明 |
| 四资源异步生态位 | 完成 | 资源和环境 vocabulary 仍固定 |
| 多尺度环境 atlas | **v0.30 完成** | 纯诊断，不是环境因果 |
| 身体/谱系/社会候选图 | 完成 | 仅一层社会群组，不是任意嵌套 |
| 社会结构 succession | **v0.30 完成** | 成员重叠关系，不是主体身份定理 |
| 结构—环境 multi-seed analysis | **v0.30 完成** | 观察性、时间和人口混杂仍存在 |
| K1–K4、L1/L2、记忆、Top-k | 完成 | 固定 action/feature vocabulary |
| group/region/anchor provenance | v0.29 完成 | 测量协议改变必须新 schema/hash |
| event-timed paired execution | 完成 | 自然 exposure 本身未随机化 |
| 任意嵌套主体数据库 | 未完成 | 当前 graph 不支持 group-of-groups |
| 主体性评分 | 未完成 | 不允许由 persistence 或 association 单指标推出 |
| 任意环境/信息通道 schema | 未完成 | 当前资源 4、危险/社会通道固定 |
| Hero RL、多 GPU | 未完成 | 当前非科学优先级 |

## 当前科学解释

1. 现有 event-timed 108/108 pairs 支持知识传播维持短期局部文化状态，但不证明人口收益。
2. 群组标签是有向有限轮候选分组；succession 只是该测量规则下的成员集合连续性。
3. 多尺度 atlas 描述环境状态空间和实现暴露，不证明环境选择或主体主动选址。
4. lineage/social association 必须结合 covered fraction；singleton 主导时不解释。
5. structure–environment 相关可能由迁移、谱系历史、人口瓶颈和共同时间趋势产生。
6. 在获得三 seed 长跑的动态范围前，不引入新的主体层级或环境机制。

## 新主线配置

```text
configs/mvp_short_subject_structure_multienvironment_atlas_longrun.json
```

该配置保留既有 flagship 动力学，只新增诊断输出和 2×2/4×4/8×8 atlas。

## 验证状态

- 全量测试：`142 passed, 1 skipped`；
- 跳过项：真实 CUDA/CuPy 设备测试；
- 定向 smoke 已产生 succession、atlas、run manifest 和 long-run v9 输出；
- 默认 v0.29/v0.30 世界轨迹和 trusted checkpoint 兼容性已记录于 `docs/v0.30/V029_V030_COMPATIBILITY_REPORT.json`；
- 新诊断默认关闭，因此旧配置不会产生额外 evolution-progress 字段。

## 下一阶段

1. 运行三 seed、1500-tick 新主线配置，检查 succession/atlas 动态范围；
2. 对同步环境与异步多生态位环境做预注册消融；
3. 对 group rounds/threshold/min-members/refresh schedule 做 schema-level 敏感性；
4. 仅在结构指标跨 seed、跨尺度重复后，设计结构删除和环境相位 paired interventions；
5. 任意嵌套主体与任意环境通道保持后续架构主线，不在当前阶段直接写入世界。
