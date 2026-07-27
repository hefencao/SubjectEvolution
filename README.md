# SE v0.49

`SE` 是围绕多维环境、可遗传功能组合、生态分化、动态知识与候选主体结构构建的可审计演化模拟参考实现。

## 本轮结构决策

D2-I 的 1500-tick 配对结果表明，v2 前馈耦合在三个 seed 中都被使用，覆盖三个下游层级，并在每个 seed 中改变约 41–60% 实体的模块激活。组合分支的有效谱系数在三个 seed 中都更高、最大谱系占比都更低，因此组合层不是沉默机制。

但组合分支的资源亲和与功能采集偏好有效维度在三个 seed 中都下降。层级和联合依赖被同一个四通道采集输出空间吸收，没有产生新的功能轴。v0.49 因而保留 v2 组合图，并新增版本化具身输出，而不是继续在“模块审计”和“环境审计”之间切换。

## v3 组合具身模块

新 schema：

- `expression-gated-compositional-embodied-v3`
- `harvest-locomotion-signal-repair-v1`

四个固定模块现在可以同时路由到：

- 原有四通道采集 residual；
- 移动功率：调节已有移动动作的速度，并按速度平方支付移动能耗；
- 场信号功率：调节已有资源、危险和社会场信号强度，并支付相应信号能耗；
- 修复驱动：显式消耗材料和能量后恢复完整性。

这些端口没有预设生态角色。模块间六条可遗传前馈耦合仍然存在，因此弱上游模块可以通过强下游模块共同控制多个物理后果。

`neutralize-functional-module-embodied-output` 只关闭三类具身输出，保留相同基因、突变、表达、组合耦合、采集输出和结构成本。

## Conda editable 工作流

本轮增加 console entry，升级后运行一次：

```bash
conda activate <your-env>
make conda-sync
```

日常验证：

```bash
make test
make conda-check
```

## D2-J 具身能力实验

```bash
se-d2-embody \
  --config configs/mvp_short_d2j_embodied_modules_longrun.json \
  --seeds 49001,49002,49003 \
  --output analyses/d2j_embodied_capability_1500 \
  --backend gpu \
  --until-tick 1500
```

该实验回答的是：组合模块是否实际使用多个物理端口，以及 harvest + embodied 的联合输出基底是否形成更高维的可遗传功能差异。它不是生态位或模块复制门槛。

## 当前科学主线

1. D0–D1：四资源环境、遗传亲和和弹性容量继续作为物理基底。
2. D2 v1：已归档的独立加法模块证据不能覆盖组合依赖。
3. D2-I v2：已证明组合层被使用，但 harvest-only vocabulary 压缩了功能维度。
4. D2-J v3：检验组合层能否共同利用移动、信号、修复与采集多个物理端口。
5. 只有功能输出基底真实扩展后，才重新检查环境关联、共存与移除反事实。
6. 模块复制、动态拓扑和任意 routing 继续阻塞。

## 文档

- [项目总规范](docs/PROJECT_CHARTER.md)
- [当前状态](docs/PROJECT_STATUS.md)
- [D2-I 结果解释](docs/v0.49/D2I_RESULT_INTERPRETATION.md)
- [D2-J 机制设计](docs/v0.49/D2J_EMBODIED_MODULE_DESIGN.md)
- [D2-J 运行计划](docs/v0.49/D2J_EMBODIED_CAPABILITY_PLAN.md)
