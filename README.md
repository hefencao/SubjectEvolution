# SE v0.46

`SE` 是围绕多维环境、可遗传分化、动态知识与候选主体结构构建的可审计演化模拟参考实现。

## Conda 本地工作流

v0.46 新增两个 D2-H console entry，并升级 D2-G 评估语义；升级后需要在目标环境执行一次：

```bash
conda activate <your-env>
make conda-sync
```

之后普通源码修改直接生效。日常验证使用：

```bash
make test
make conda-check
```

不要在正常 Conda editable 工作流中设置 `PYTHONPATH=src`，也不要把 wheel 单独安装作为日常开发方式。

## 主要运行入口

```bash
se --config <CONFIG> --seed 10001 --output <DIR> --backend cpu
```

```bash
se-multi \
  --config configs/mvp_short_d2a_contextual_harvest_longrun.json \
  --seeds 10001,10002,10003 \
  --checkpoint-ticks 2400,2640,2760,2820,2880,3000 \
  --until-tick 3000 \
  --output runs/d2a_contextual_modules_multiseed \
  --backend gpu
```

## D2-B/C 模块审计与效应判定

`se-d2-audit` 生成共享 checkpoint 的逐模块中和分支；`se-d2-assess` 对 120/300-tick 结果实施实用阈值、重复性、即时足迹和谱系 guard 判定。

```bash
se-d2-assess \
  --short-results analyses/d2b_module_audit_120/d2_module_audit_results.json \
  --long-results analyses/d2b_module_audit_300/d2_module_audit_results.json \
  --output analyses/d2c_effect_assessment \
  --refresh-footprints
```

## D2-D/E 多谱系配对审计

```bash
se-d2-lineage-pairs \
  --results analyses/d2b_module_audit_300/d2_module_audit_results.json \
  --output analyses/d2d_lineage_pairs_120 \
  --modules 2,3 \
  --horizon 120 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

```bash
se-d2-lineage-assess \
  --short-results analyses/d2d_lineage_pairs_120/d2_lineage_pair_results.json \
  --long-results analyses/d2e_lineage_pairs_300/d2_lineage_pair_results.json \
  --output analyses/d2e_lineage_pair_persistence
```

本次 300-tick 判定中，模块 2 的 120-tick 输出信号没有跨 horizon 持续；模块 3 仅保留目标谱系平均能量的正向 routed-output 效应。存活效应在 120 与 300 ticks 之间反向，因此不能把平均能量提升直接解释为生态收益。

## D2-F 时间中介审计

从已确认的 D2-E 评估和原 300-tick 计划生成 D2-F 计划：

```bash
se-d2-lineage-mediate \
  --assessment analyses/d2e_lineage_pair_persistence/d2_lineage_pair_assessment.json \
  --source-plan analyses/d2e_lineage_pair_assessment/d2_lineage_pair_confirmation_plan.json \
  --output analyses/d2f_lineage_mediation_plan
```

默认保留模块 3 在 6 个 checkpoint 中的全部 24 个预选谱系配对，并在 30、60、120、180、240、300 ticks 采样。执行：

```bash
se-d2-lineage-mediate \
  --plan analyses/d2f_lineage_mediation_plan/d2_lineage_mediation_plan.json \
  --output analyses/d2f_lineage_mediation_trajectory \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

完成后判定中介链：

```bash
se-d2-lineage-mediate-assess \
  --results analyses/d2f_lineage_mediation_trajectory/d2_lineage_mediation_results.json \
  --output analyses/d2f_lineage_mediation_assessment
```

D2-F 同时报告：

- 平均能量、总能量与能量分位数；
- 源成员幸存、存活后代、出生与按原因死亡；
- 生育度和繁殖就绪数量；
- 干预后的累计采集能量与共享能量；
- routed-output、保留表达成本和总表达三类效应。

多个时间点是同一配对单元的重复观测，不能增加 seed 或谱系复制数。平均能量只有在总能量、输入流和人口转换同时报告后才可解释。

## D2-G 源群体重构与资格审计

D2-F 显示模块 3 存在短暂的流量—能量—人口转换，但原 300-tick 终点未在最终偏移复现，源 checkpoint 仍由少数谱系主导。D2-G 不复制模块，而是从三个独立源 seed 的预干预谱系构建新的遗传创始者面板。

```bash
se-d2-source-population \
  --assessment analyses/d2f_lineage_mediation_assessment/d2_lineage_mediation_assessment.json \
  --mediation-results analyses/d2f_lineage_mediation_trajectory/d2_lineage_mediation_results.json \
  --output analyses/d2g_source_population_plan
```

```bash
se-d2-source-population \
  --plan analyses/d2g_source_population_plan/d2_source_population_plan.json \
  --output analyses/d2g_source_population_burnin \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

```bash
se-d2-source-population-assess \
  --results analyses/d2g_source_population_burnin/d2_source_population_results.json \
  --output analyses/d2g_source_population_assessment
```

自然丰度对照和等谱系重构臂使用相同总创始者数、同一新世界 seed 和唯一供体基因型。等谱系只发生在 tick 0；之后没有谱系奖励、保护、空间保留或繁殖干预。

v0.46 明确区分探索性实验门控与主要结论。`PROJECT_CHARTER.md` 的 10-seed 下限约束主要结论，并不要求每个探索性审计都先运行 10 seeds。当前 3-seed 配对结果中，peak 等谱系臂为 2/3、自然丰度对照为 0/3；trough 为 1/3 与 0/3。该结果足以把 peak 路由到下一次探索性共享 checkpoint 因果复审，但置信区间很宽，不能宣称一般源群体已确证。

## D2-H 重设计源群体中的模块 3 因果复审

先使用 v0.46 重新评估 D2-G：

```bash
se-d2-source-population-assess \
  --results analyses/d2g_source_population_burnin/d2_source_population_results.json \
  --output analyses/d2g_source_population_assessment_v2
```

从评估和原始结果生成 120-tick 计划：

```bash
se-d2-source-causal \
  --assessment analyses/d2g_source_population_assessment_v2/d2_source_population_assessment.json \
  --results analyses/d2g_source_population_burnin/d2_source_population_results.json \
  --output analyses/d2h_source_population_causal_120
```

执行：

```bash
se-d2-source-causal \
  --plan analyses/d2h_source_population_causal_120/d2_source_population_causal_plan.json \
  --output analyses/d2h_source_population_causal_120 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

评估 120-tick 结果，并在满足预注册 routed-output 重复性时自动生成 300-tick 确认计划：

```bash
se-d2-source-causal-assess \
  --results analyses/d2h_source_population_causal_120/d2_source_population_causal_results.json \
  --output analyses/d2h_source_population_causal_assessment_120
```

D2-H 仅使用 peak 中通过既有绝对 guard 的两个等谱系 checkpoint（fresh-world seeds 45001、45003），保留其中全部 6 条成员与表达合格谱系。面板和谱系均不按 D2-G 响应幅度筛选。每个 module-lineage 对仍使用 baseline、output-neutral、expression-neutral 三分支，复制数和 routing vocabulary 均不改变。

## 当前科学主线

1. **D0：** 正交四资源环境。
2. **D1：** 可遗传弹性容量。
3. **D1-B：** affinity 驱动的单通道选择性采集。
4. **D1-C：** 请求资源、实际采集资源和 affinity × capacity 因子实验。
5. **D2-A：** 四个固定布局、可遗传、表达门控的上下文采集模块。
6. **D2-B：** 逐模块贡献审计和逐模块中和实验。
7. **D2-C：** 下游效应判定、即时足迹刷新和复制门槛。
8. **D2-D：** 谱系定向输出/成本三分支配对。
9. **D2-E：** 非主导谱系跨 seed、跨 horizon 持续性判定。
10. **D2-F：** routed-output 的采集/共享—能量—繁殖—存活时间中介审计。
11. **D2-G：** 跨源 seed 的遗传创始者面板、自然丰度对照和无保护 burn-in 探索性资格审计。
12. **D2-H：** 在 phase-qualified 重设计 checkpoint 中重新估计模块 3 的 routed-output 与表达成本因果效应。

模块复制、删除、任意重联和新端口继续阻塞。D2-G 只改变显式实验的 tick-zero 遗传起点；D2-H 只在冻结 checkpoint 的实验分支中中和既有模块输出/成本。普通世界路径不读取面板谱系，也不提供持续多样性保护。

## 文档

- [项目立项](docs/PROJECT_CHARTER.md)
- [架构与提交边界](docs/ARCHITECTURE.md)
- [项目状态](docs/PROJECT_STATUS.md)
- [科学问题](docs/SCIENTIFIC_ISSUES.md)

- [D2-H 设计与证据边界](docs/v0.46/D2H_SOURCE_POPULATION_CAUSAL_REAUDIT.md)
- [D2-G v2 真实评估](docs/v0.46/D2G_EXPLORATORY_ASSESSMENT.md)
- [生成的 D2-H 计划](docs/v0.46/D2H_SOURCE_POPULATION_CAUSAL_PLAN.md)
- [下一步运行](docs/v0.46/NEXT_EXPERIMENT.md)
- [Conda editable 工作流](docs/v0.46/CONDA_EDITABLE_WORKFLOW.md)
