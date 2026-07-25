# Subject Evolution 项目状态（v0.23.0）

## 本轮结论

用户完成 mortality-trace + adaptive-groups + costed-transfer 旗舰配置的 3-seed、1500-tick 长跑。传播提交达到 `12,208–14,428`，有效 transferred roots 达到 `2,066.55–2,243.77`，证明知识能够跨主体持续传播；但 transfer/no-transfer 的全局人口、遗传世系、策略维度与凝聚度差异较小，尚无稳健全局收益结论。

本轮不继续增加“生物性危险源”。任何具有出生、死亡、策略、关系、记忆或谱系的危险主体，都应由现有实体系统分化，而不是在环境层复制一套生物机制。

## v0.23 核心改动

### 环境过程插件边界

新增：

```text
additive-environment-field-process-v1
```

核心只允许插件返回有限、非负、同网格形状的 hazard 标量增量。插件无法读取实体、关系、群组、谱系、策略、知识、记忆或生命周期，也没有行动/伤害提交钩子。

### moving Gaussian 降级

v0.22 的：

```text
moving-gaussian-hazard-sources-v1
```

已从 CPU/GPU 环境核心分支移出，成为默认关闭的兼容插件。数值公式不变，旧配置与 checkpoint 可继续运行。

其解释标签为：

```text
synthetic-observation-or-entertainment-extension
```

启用后运行仍可用于观察、重放和游戏实验，但 `scientific_validity.json` 会明确将其排除出科学生态基线。

### 科学旗舰配置

配置：

```text
mvp_short_latent_l2_memory_topk_inherited_heterogeneous_budget_matched_costed_transfer_mortality_trace_adaptive_groups_longrun.json
```

现在显式声明：

```json
"environment_process_schema": "disabled",
"environment_process_parameters": {}
```

因此当前科学方向只依赖现有资源异质性、权威 hazard、局部死亡痕迹、拥挤、社会关系、知识传播和主体自身演化。

### 长期分析 v7

`multi-seed-long-run-analysis-v7` 新增环境过程 provenance：schema、来源、机制分类、解释标签和参数名。分析器只读取 manifest/config，不加载插件代码。

## 兼容性与验证

- 全量测试：`117 passed, 1 skipped`；
- 跳过项：真实 CUDA/CuPy 设备测试；
- disabled 科学基线 v0.22→v0.23：308 个共同非计时 metrics 字段完全一致；
- v0.22 moving-hazard 核心→v0.23 兼容插件：308 个共同非计时 metrics 字段完全一致；
- 两种条件下 7 类知识/事件日志均 byte-identical；
- generic 插件配置与 v0.22 legacy 字段生成相同 hazard；
- 旧 checkpoint 配置哈希兼容通过；恢复时按嵌入配置重建插件对象。

## 已完成能力

| 能力 | 状态 |
|---|---|
| K1–K4 动态知识、成本、副本、策略 residual、内容谱系 | 完成 |
| checkpoint、恢复、离线配对反事实 | 完成 |
| 潜知识 L1/L2、计算成本、工作记忆、遗传 Top-k | 完成 |
| 空间异步多资源生态位与固定预算亲和 | 完成 |
| 长期选择、局部压力、局部文化流与 transfer-only 根谱系 | 完成 |
| 局部死亡痕迹与自适应群组刷新 | 完成 |
| 遗传 direct/trace 证据混合与中和干预 | 完成 |
| 低耦合环境标量场插件边界 | **完成** |
| 真实 CUDA hybrid world 多 tick parity | 未完成 |
| 通用任意信息通道 schema | 未实现 |
| 通用主体图数据库与任意嵌套主体 | 未实现 |

## 下一阶段优先级

1. 不改变世界规则，先对这 3 个 seed 的局部稀缺、拥挤、死亡痕迹和文化根事件做 checkpoint 对齐；
2. 在同一局部事件相位执行 transfer、working-memory、Top-k、danger-evidence 与 group-refresh 配对干预；
3. 推进通用信息通道 schema，使新增环境证据不必绑定固定 danger 通道；
4. 将游戏化的追踪者、灾害脚本或社会循环放入独立插件包，不写入科学核心；
5. 单独完成真实 CUDA hybrid parity，不与机制解释混合。

继续暂不采用：按群组/谱系奖励、自动保护多样性、全局类别 embedding、普通 Softmax Attention、跨组惩罚、单纯提高 mutation rate，以及在环境层复制第二套生物实体。
