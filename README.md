# SE v0.42

`SE` 是围绕多维环境、可遗传分化、动态知识与候选主体结构构建的可审计演化模拟参考实现。

## Conda 本地工作流

升级到 v0.42 后，因为新增 `se-d2-lineage-pairs` 入口，需要在目标环境执行一次：

```bash
conda activate <your-env>
make conda-sync
```

之后普通源码修改直接生效，不需要重新安装 wheel。日常测试：

```bash
make test
```

长跑或交付前：

```bash
make conda-check
```

不要在正常 conda 工作流中设置 `PYTHONPATH=src`；这可能掩盖 stale editable metadata 或旧 console script。

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

## D2 模块审计

生成 leave-one-module-out 分支：

```bash
se-d2-audit \
  --run-dir runs/d2a_contextual_modules_multiseed/seed_10001 \
  --run-dir runs/d2a_contextual_modules_multiseed/seed_10002 \
  --run-dir runs/d2a_contextual_modules_multiseed/seed_10003 \
  --output analyses/d2b_module_audit_120 \
  --phases peak,trough \
  --horizon 120 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

120 ticks 完成后，不再人工判断是否需要 300 ticks：

```bash
se-d2-assess \
  --results analyses/d2b_module_audit_120/d2_module_audit_results.json \
  --output analyses/d2c_screen_120
```

若输出 `run-300-tick-confirmation`，再执行 300 ticks。已有 120/300 结果可直接合并评估：

```bash
se-d2-assess \
  --short-results analyses/d2b_module_audit_120/d2_module_audit_results.json \
  --long-results analyses/d2b_module_audit_300/d2_module_audit_results.json \
  --output analyses/d2c_effect_assessment \
  --refresh-footprints
```

`--refresh-footprints` 只读取结果文件引用的源 checkpoint，计算即时、按谱系分解的 HARVEST 接口足迹；不会重跑 120/300-tick 分支。

## D2-D 多谱系配对审计

先从现有 D2-B 结果和其引用的共享 checkpoint 生成计划；默认只选择干预前成员数不少于 8 的最大四个谱系，并要求每个 checkpoint 至少三个合格谱系：

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

每个 checkpoint × module × lineage 使用 `baseline`、`output-neutral`、`expression-neutral` 三个共享随机性分支。谱系保持世界中的自然丰度；只在离线汇总 checkpoint-lineage 配对效应时等权，不奖励、不保护也不补齐多样性。

## 当前科学主线

1. **D0：** 四资源具有独立外生空间、时间与扩散过程。
2. **D1-A：** 工作记忆、知识、关系与注意力容量可遗传、计费和消融。
3. **D1-B：** 固定采集预算下，由遗传 affinity 采样单一资源通道。
4. **D1-C：** 请求流与实现流分离；共享 checkpoint 的 affinity × capacity 因子实验。
5. **D2-A：** 四个表达门控上下文模块发布有限零和采集权重残差。
6. **D2-B：** 独立模块贡献诊断与逐模块消融。
7. **D2-C：** 数值差异、实用效应、跨 seed 复现、即时足迹与跨谱系证据分层判定。
8. **D2-D：** 在谱系集中条件下，用共享 checkpoint 的谱系定向三分支配对分离模块输出作用与表达成本退款。

刷新后的 120/300-tick 结果已经显示四个模块均有跨谱系即时足迹，模块 1–3 有重复生态效应；但中位有效谱系仍约为 2.03。模块复制、删除、任意重联和新物理端口继续阻塞，下一步是模块 2/3 的多谱系配对审计。

## 文档

- [项目立项](docs/PROJECT_CHARTER.md)
- [架构与提交边界](docs/ARCHITECTURE.md)
- [项目状态](docs/PROJECT_STATUS.md)
- [科学问题](docs/SCIENTIFIC_ISSUES.md)
- [D2-D 多谱系配对设计](docs/v0.42/D2D_LINEAGE_BALANCED_PAIRING.md)
- [输入 D2-C 评估与决策](docs/v0.42/ASSESSMENT_DECISION.md)
- [下一步实验计划](docs/v0.42/NEXT_EXPERIMENT.md)
- [Conda editable 工作流](docs/v0.42/CONDA_EDITABLE_WORKFLOW.md)
