# SE v0.47

`SE` 是围绕多维环境、可遗传分化、生态位、动态知识与候选主体结构构建的可审计演化模拟参考实现。

## Conda editable 工作流

v0.47 更新版本元数据并新增两个 console entry，升级后需要在目标 Conda 环境执行一次：

```bash
conda activate <your-env>
make conda-sync
```

日常验证：

```bash
make test
make conda-check
```

不再把 wheel 单独安装作为日常开发流程。`make release-check` 仅用于隔离发行物审计。

## 普通模拟入口

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

## D2 结论：停止模块复制路线

D2-B 至 D2-H 依次完成了逐模块消融、跨谱系配对、120/300-tick 持续性、时间中介、遗传创始者重构和重构 checkpoint 中的模块 3 复审。

最新 D2-H 结果为：

- 使用 peak fresh-world seeds `45001`、`45003`；
- 每个 checkpoint 保留全部 6 条预注册合格谱系；
- 共执行 12 个 module-3 × lineage 三分支配对；
- 模块 3 没有形成跨 seed、跨非主导谱系的重复 routed-output 效应；
- 仅存在表达成本相关信号，不能替代模块输出因果证据；
- 不生成 300-tick 模块确认计划；
- 模块复制、删除、任意重联和新 output port 继续阻塞。

因此 v0.47 不再围绕模块复制追加同类实验，主线进入 charter 的 D4 生态位形成阶段。

## D4-A：资源地理 × 遗传亲和反转审计

新增入口：

```bash
se-d4-niche-reversal
se-d4-niche-assess
```

D4-A 从 D2-H 已冻结的两个多谱系 peak checkpoint 建立共享 checkpoint 的 2×2 因子实验：

1. `baseline`：原资源地理，遗传亲和正常表达；
2. `resource-reversed`：资源地理旋转 180°，亲和正常表达；
3. `affinity-neutral`：原资源地理，中和亲和表达；
4. `joint-neutral`：资源地理反转并中和亲和表达。

主要交互为：

```text
(baseline - resource-reversed)
- (affinity-neutral - joint-neutral)
```

正值表示原资源地理相对反转地理的优势中，有一部分只能在遗传亲和表达存在时出现。该差中之差排除了资源反转本身的一般扰动。

`reverse-resource-geography` 只改变资源空间地理：

- 当前四资源字段旋转 180°；
- 后续季节性再生模板持续旋转；
- 不修改资源通道身份和 effect matrix；
- 不修改 hazard 或 mortality trace；
- 不修改实体、基因型、谱系、模块或随机键。

执行 120-tick 探索性 screen：

```bash
se-d4-niche-reversal \
  --plan docs/v0.47/d4_niche_reversal_plan.json \
  --output analyses/d4a_niche_reversal_120 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

评估：

```bash
se-d4-niche-assess \
  --results analyses/d4a_niche_reversal_120/d4_niche_reversal_results.json \
  --output analyses/d4a_niche_reversal_assessment_120
```

若至少两个独立 panel seed、至少两个非主导谱系身份出现同方向的实用 affinity × environment 交互，评估器会生成保持全部 checkpoint-lineage 单元的 300-tick 确认计划。

D4-A 同时记录每条源谱系的：

- 四通道平均遗传亲和；
- 原资源地理和旋转地理下的局部资源暴露；
- affinity-specific exposure advantage；
- endpoint 存活、世界占比、能量、材料、信息和 fertility；
- 世界层面的资源维度、采集效率和有效谱系指标。

源暴露对齐只是预干预结构诊断，不被当作新的独立因果重复。即便 D4-A 跨 horizon 通过，也只证明资源地理匹配；稳定共存、生态型移除、地图尺度和空间模板检查仍是生态位结论的必要条件。

## 当前科学主线

1. **D0：** 正交四资源环境。
2. **D1：** 可遗传弹性容量与 affinity × capacity 因子设计。
3. **D2：** 固定模块表达、消融、跨谱系和源群体复审；复制路线已停止。
4. **D4-A：** 资源地理反转 × 遗传亲和表达的环境匹配因果审计。
5. **D4-B（受 D4-A 确认结果约束）：** 稳定共存和生态型/表型 cohort 移除。
6. **D5：** 仅在生态分化得到可重复证据后研究社会形成。

## 文档

- [项目总规范](docs/PROJECT_CHARTER.md)
- [架构与提交边界](docs/ARCHITECTURE.md)
- [当前状态](docs/PROJECT_STATUS.md)
- [科学问题](docs/SCIENTIFIC_ISSUES.md)
- [D2-H 停止判定](docs/v0.47/D2H_STOP_DECISION.md)
- [D4-A 设计](docs/v0.47/D4A_NICHE_REVERSAL_DESIGN.md)
- [生成的 D4-A 计划](docs/v0.47/d4_niche_reversal_plan.md)
- [下一步运行](docs/v0.47/NEXT_EXPERIMENT.md)
- [Conda editable 工作流](docs/v0.47/CONDA_EDITABLE_WORKFLOW.md)
