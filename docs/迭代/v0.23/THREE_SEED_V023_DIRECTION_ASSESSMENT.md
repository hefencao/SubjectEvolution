# v0.23 方向评估：不增加生物性危险源

## 本轮输入

用户完成了配置：

```text
mvp_short_latent_l2_memory_topk_inherited_heterogeneous_budget_matched_costed_transfer_mortality_trace_adaptive_groups_longrun.json
```

的 3-seed、1500-tick 长跑。

已有汇总显示：

- costed-transfer 条件累计提交传播 `12,208–14,428` 次；
- 有效 transferred roots 为 `2,066.55–2,243.77`；
- 三 seed 端点均值：alive `1356.67`、有效遗传世系 `19.8283`、策略有效维度 `17.5670`、动作熵 `1.7372`、凝聚度 `0.3967`；
- 与 no-transfer 对照相比，全局人口、世系、策略维度和凝聚度差异较小，方向也未形成稳健一致性。

因此，知识确实跨主体传播并形成大量文化根，但不能仅凭全局端点宣称传播带来人口或多样性收益。空间异步环境可能在全局上平滑局部压力，下一步仍应依赖局部 panel 与 checkpoint 干预。

## 用户提出的约束

危险源不应复制当前主体的生物属性。具有出生、死亡、策略、关系、记忆或谱系的危险主体，本质上可由现有实体分化得到；若在环境层再实现一套，会造成概念重复和人为设定。

因此：

1. 科学基线不新增生物性危险实体；
2. 不把 synthetic moving hazard 继续扩展为核心生态规则；
3. 仅为观察、演示或游戏化保留可选扩展；
4. 扩展必须低耦合、默认关闭、可审计、可拔除；
5. 默认科学配置只使用现有资源、权威 hazard、死亡痕迹、拥挤与社会/文化过程。

## v0.23 决策

v0.22 的 moving Gaussian 实现从 `environment.py` 与 `gpu_environment.py` 的核心分支中移除，改为环境过程插件：

```text
additive-environment-field-process-v1
```

核心只向插件提供：

- 当前 tick；
- 归一化二维周期网格；
- NumPy/CuPy 风格数组命名空间。

插件只能返回一个与 hazard 网格同形状、有限、非负的标量增量。核心不向插件提供：

- 实体数组或实体 ID；
- 行动、策略或控制接口；
- 社会关系、群组或谱系；
- 知识、工作记忆或传播状态；
- 出生、死亡或伤害提交钩子。

这个边界从结构上防止环境扩展变成第二套生物系统。

## 科学解释边界

兼容插件 `moving-gaussian-hazard-sources-v1` 被标记为：

```text
synthetic-observation-or-entertainment-extension
```

它仍可重放 v0.22 配置，也可用于可视化或游戏实验，但启用后 `scientific_validity.json` 会明确把运行排除出科学生态基线。执行仍被允许，以保留历史兼容和配对实验能力。

## 后续研究顺序

1. 保持当前 3-seed 科学配置的环境过程为 `disabled`；
2. 从自然发生的局部稀缺、拥挤、死亡痕迹和文化根变化中选择 checkpoint；
3. 对 transfer、working memory、Top-k、danger evidence 和 group refresh 做局部事件对齐的配对干预；
4. 优先推进通用信息通道 schema 与局部事件索引，不再添加拟生物危险源；
5. 游戏化社会循环可在独立插件包中实现追踪、敌对主体或灾害脚本，但不得复用科学结果标签。
