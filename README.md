# SE v0.44

`SE` 是围绕多维环境、可遗传分化、动态知识与候选主体结构构建的可审计演化模拟参考实现。

## Conda 本地工作流

v0.44 新增两个 D2-F console entry，升级后需要在目标环境执行一次：

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

模块复制、删除、任意重联和新端口继续阻塞。D2-F 只增加实验观察，不给多样性奖励，不预设生态角色，不修改世界中的模块数量或路由词汇。

## 文档

- [项目立项](docs/PROJECT_CHARTER.md)
- [架构与提交边界](docs/ARCHITECTURE.md)
- [项目状态](docs/PROJECT_STATUS.md)
- [科学问题](docs/SCIENTIFIC_ISSUES.md)
- [D2-F 设计与当前判定](docs/v0.44/D2F_TEMPORAL_MEDIATION.md)
- [输入的 300-tick 评估](docs/v0.44/INPUT_D2E_LINEAGE_PAIR_ASSESSMENT.md)
- [生成的 D2-F 计划](docs/v0.44/D2F_MEDIATION_PLAN.md)
- [下一步运行](docs/v0.44/NEXT_EXPERIMENT.md)
- [Conda editable 工作流](docs/v0.44/CONDA_EDITABLE_WORKFLOW.md)
