# SE v0.43

`SE` 是围绕多维环境、可遗传分化、动态知识与候选主体结构构建的可审计演化模拟参考实现。

## Conda 本地工作流

v0.43 新增 `se-d2-lineage-assess` 入口，升级后需要在目标环境执行一次：

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

## D2 模块审计与效应判定

`se-d2-audit` 生成共享 checkpoint 的逐模块中和分支；`se-d2-assess` 对 120/300-tick 结果实施实用阈值、重复性、即时足迹和谱系 guard 判定。

```bash
se-d2-assess \
  --short-results analyses/d2b_module_audit_120/d2_module_audit_results.json \
  --long-results analyses/d2b_module_audit_300/d2_module_audit_results.json \
  --output analyses/d2c_effect_assessment \
  --refresh-footprints
```

## D2-D/D2-E 多谱系配对审计

从 D2-B 源 checkpoint 生成并执行 120-tick 多谱系三分支配对：

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

D2-E 自动判定是否值得继续，并在通过时生成不按单个谱系响应挑选的 300-tick 计划：

```bash
se-d2-lineage-assess \
  --results analyses/d2d_lineage_pairs_120/d2_lineage_pair_results.json \
  --output analyses/d2e_lineage_pair_assessment
```

执行生成的确认计划：

```bash
se-d2-lineage-pairs \
  --plan analyses/d2e_lineage_pair_assessment/d2_lineage_pair_confirmation_plan.json \
  --output analyses/d2e_lineage_pairs_300 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

完成后进行跨 horizon 持续性判定：

```bash
se-d2-lineage-assess \
  --short-results analyses/d2d_lineage_pairs_120/d2_lineage_pair_results.json \
  --long-results analyses/d2e_lineage_pairs_300/d2_lineage_pair_results.json \
  --output analyses/d2e_lineage_pair_persistence
```

只有 `output_routing_effect` 能通过继续门槛。表达成本退款或总表达差异不能替代输出作用证据。确认计划只筛选模块，并保留该模块在原计划中的全部 checkpoint-lineage 配对。

## 当前科学主线

1. **D0：** 正交四资源环境。
2. **D1：** 可遗传弹性容量。
3. **D1-B：** affinity 驱动的单通道选择性采集。
4. **D1-C：** 请求资源、实际采集资源和 affinity × capacity 因子实验。
5. **D2-A：** 四个固定布局、可遗传、表达门控的上下文采集模块。
6. **D2-B：** 逐模块贡献审计和逐模块中和实验。
7. **D2-C：** 下游效应判定、即时足迹刷新和复制门槛。
8. **D2-D：** 谱系定向输出/成本三分支配对。
9. **D2-E：** 非主导谱系跨 seed 复现判定和不挑选响应谱系的 300-tick 确认。

用户提供的 120-tick D2-D 结果使模块 2、3 进入 300-tick 确认，但没有建立正向生态收益：模块 2 的重复信号是知识转移根数下降；模块 3 同时表现为目标谱系存活下降和平均能量上升。谱系 guard 仍失败，模块复制、删除、任意重联和新端口继续阻塞。

## 文档

- [项目立项](docs/PROJECT_CHARTER.md)
- [架构与提交边界](docs/ARCHITECTURE.md)
- [项目状态](docs/PROJECT_STATUS.md)
- [科学问题](docs/SCIENTIFIC_ISSUES.md)
- [D2-E 判定规则](docs/v0.43/D2E_LINEAGE_PAIR_QUALIFICATION.md)
- [输入结果自动评估](docs/v0.43/INPUT_D2D_LINEAGE_PAIR_ASSESSMENT.md)
- [300-tick 确认计划](docs/v0.43/D2E_CONFIRMATION_PLAN.md)
- [下一步实验](docs/v0.43/NEXT_EXPERIMENT.md)
- [Conda editable 工作流](docs/v0.43/CONDA_EDITABLE_WORKFLOW.md)
