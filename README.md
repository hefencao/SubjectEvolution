# SE v0.48

`SE` 是围绕多维环境、可遗传功能组合、生态分化、动态知识与候选主体结构构建的可审计演化模拟参考实现。

## 本轮方向修正

v0.47 的 D4-A 运行出现了重复的 affinity × resource-geography 终点交互，但源谱系的资源暴露差异很小，且没有任何 exposure-aligned outcome。该结果说明分支可以因果分离一般交互，却不能证明已经形成不同资源生态位。v0.48 因此取消 D4-A 的 300-tick 自动确认，不再用“环境不满足 → 回模块审计 → 模块不满足 → 回环境审计”的方式推进。

结构复核发现，旧 `expression-gated-contextual-harvest-v1` 的四个模块都是独立加法项：同一组输入、同一零和采集 residual 端口、无模块间信号、无层级和无联合功能。它能表达参数差异和加法混合，但不足以检验弱模块被强模块携带、组合依赖或同功能模块的层级表现。

v0.48 新增有界组合架构：

- `expression-gated-compositional-harvest-v2`；
- 四个固定槽位不变；
- 六个可遗传、可突变且有明确成本的前馈 coupling genes；
- 低槽位信号可放大或抑制高槽位的上下文激活；
- 每个模块仍可直接发布采集 residual；
- 不增加资源、传感器、动作、世界物理、模块复制数或任意 routing；
- v1 配置继续走原始权威加法路径。

这使同一采集功能的模块能够出现不同层级：上游模块可以直接输出很弱，却通过下游模块产生组合效应。v2 仍只作用于采集请求，因此它是组合功能能力扩展，不是完整具身功能分化。

## Conda editable 工作流

v0.48 更新元数据并新增 `se-d2-compose`，升级后运行一次：

```bash
conda activate <your-env>
make conda-sync
```

日常验证：

```bash
make test
make conda-check
```

## D2-I 组合能力实验

```bash
se-d2-compose \
  --config configs/mvp_short_d2i_compositional_harvest_longrun.json \
  --seeds 48001,48002,48003 \
  --output analyses/d2i_compositional_capability_1500 \
  --backend gpu \
  --until-tick 1500
```

每个 seed 从相同 v2 初始分布运行两个新群体：

- `composition-active`：前馈组合正常；
- `coupling-neutral`：保留相同 coupling genes、突变和结构成本，只关闭组合输出。

该实验不是复制门槛或生态位合格审计，而是回答：演化是否实际利用组合通路、是否形成多层级介导信号、是否降低单模块支配或增加功能采集偏好的有效维度。

解释顺序：

1. coupling 未被利用：先校准表达、突变和成本；
2. coupling 被利用但功能维度不增加：共享的 harvest-only 输出词汇是下一瓶颈；
3. coupling 被利用且功能差异持续扩大：保留 v2 演化群体，再进行环境匹配实验；
4. 只有生态终点分支而无功能差异：视为轨迹放大，不视为分化。

## 当前科学主线

1. **D0–D1：** 四资源环境、遗传亲和与弹性容量继续作为现有物理基底。
2. **D2 archived evidence：** 旧 v1 模块的输出、成本和谱系效应已有审计，但不能回答组合架构能力。
3. **D2-I：** 先验证有界组合模块是否被演化利用，以及同功能模块能否形成层级和联合依赖。
4. **D4-A deferred：** 上传的 120-tick 结果没有 exposure-aligned differentiation，不执行旧 300-tick confirmation。
5. **下一结构决策：** 若 v2 被利用但仍无多维功能差异，扩展版本化具身 primitive/output vocabulary；不得机械切回环境反转。
6. **生态位与社会：** 仅在功能分化和环境匹配形成可重复证据后继续。

## 文档

- [项目总规范](docs/PROJECT_CHARTER.md)
- [架构边界](docs/ARCHITECTURE.md)
- [当前状态](docs/PROJECT_STATUS.md)
- [科学问题](docs/SCIENTIFIC_ISSUES.md)
- [结构能力复核](docs/v0.48/CAPABILITY_REASSESSMENT.md)
- [D2-I 组合模块设计](docs/v0.48/D2I_COMPOSITIONAL_MODULE_DESIGN.md)
- [D4-A 重新判定](docs/v0.48/D4A_REASSESSMENT.md)
- [下一步运行](docs/v0.48/NEXT_EXPERIMENT.md)
