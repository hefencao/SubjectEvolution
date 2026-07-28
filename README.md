# SE v0.51

`SE` 是围绕多维环境、可遗传功能组合、生态分化、动态知识与候选主体结构构建的可审计演化模拟参考实现。

## 本轮设计修正

v0.50 的四种粗粒度身体驱动只适合作为原型。v0.51 参考项目 charter 与新的设计讨论，将系统改为明确的分层因果生成模型：

```text
遗传功能算子
→ 调控请求
→ 遗传运输/储备/转换/清除/修复参数
→ 氧合、疲劳、组织、结构、信使与有限前体
→ 实际移动、感知、信号、损伤与修复
```

模块不再直接声明移动、信号或修复能力。它们只发布氧摄取调制、动员信使刺激、维护信使刺激和感知注意调制。两个抽象信使通路具有独立可遗传的合成、衰减与受体参数，但竞争同一个有限前体池。

v0.51 保留固定权重、表达门控、前馈组合和确定性离散时间更新；不引入在线 Hebbian、Gumbel 训练、任意递归网络、具名激素、器官或多细胞类型。

## 可审计反事实

新增：

- `neutralize-functional-module-physiology-output`
- `block-physiology-messenger-receptors`
- `Simulation.set_physiology_state_clamp(...)`

这些干预不修改 genotype，不改变随机流，并随完整 checkpoint 和 clone 持久化。

## Conda editable 工作流

元数据和入口已变化，升级后运行一次：

```bash
conda activate <your-env>
make conda-sync
```

日常验证：

```bash
make test
make conda-check
```

## D2-L 运行

```bash
se-d2-regulatory-physiology \
  --config configs/mvp_short_d2l_regulatory_physiology_longrun.json \
  --seeds 51001,51002,51003 \
  --output analyses/d2l_regulatory_physiology_1500 \
  --backend gpu \
  --until-tick 1500
```

D2-L 不设置“模块充分表达”门槛。它用于继续演化并保存 v5 群体，同时记录遗传生理差异、信使周转、有限前体、计算代价、疲劳与损伤/修复流。成熟生态位、食物链和模块复制仍需后续完整生态链。

## 文档

- [项目总规范](docs/PROJECT_CHARTER.md)
- [当前状态](docs/PROJECT_STATUS.md)
- [设计复核](docs/v0.51/DESIGN_REASSESSMENT.md)
- [D2-L 生理设计](docs/v0.51/D2L_REGULATORY_PHYSIOLOGY_DESIGN.md)
- [D2-L 运行计划](docs/v0.51/D2L_REGULATORY_PHYSIOLOGY_PLAN.md)
