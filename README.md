# SE v0.39

`SE` 是围绕多维环境、可遗传分化、动态知识与候选主体结构构建的可审计演化模拟参考实现。

## 安装与发行验证

`make release-check` 使用一次性 venv，只验证发行包，结束后不会修改当前 zsh 的 `PATH`。因此它通过后，当前 shell 中仍可能没有 `se-d1-factorial`。

需要保留可运行环境时使用：

```bash
make release-env \
  PREVIOUS_WHEEL=/path/to/se_mvp-0.38.0-py3-none-any.whl
source .release-env/venv/bin/activate
```

也可以不激活，直接运行：

```bash
.release-env/venv/bin/se-d1-factorial --help
```

`release-env` 会完成源码测试、sdist→wheel 构建、旧 wheel 覆盖安装、源码树外导入、全模块导入、CLI、单 seed、多 seed 精确 checkpoint 与短程模拟验证。

## 单次与多 seed 运行

单次运行可直接覆盖 seed，并指定多个精确 checkpoint：

```bash
se \
  --config configs/d2a_contextual_harvest_smoke.json \
  --seed 10001 \
  --checkpoint-ticks 120,240,360 \
  --until-tick 360 \
  --output runs/d2a_seed_10001 \
  --backend cpu
```

多 seed 会为每个 seed 写出同一组 checkpoint：

```bash
se-multi \
  --config configs/mvp_short_d2a_contextual_harvest_longrun.json \
  --seeds 10001,10002,10003 \
  --checkpoint-ticks 2400,2640,2760,2820,2880,3000 \
  --until-tick 3000 \
  --output runs/d2a_multiseed \
  --backend gpu
```

每个 seed 写出 checkpoint tick 的并集；某个 seed 暂时不需要的额外 checkpoint 不影响世界语义。

## D1 因子实验

自动选择人口周期：

```bash
se-d1-factorial \
  --run-dir runs/d1c_multiseed/seed_10001 \
  --run-dir runs/d1c_multiseed/seed_10002 \
  --run-dir runs/d1c_multiseed/seed_10003 \
  --output analyses/d1_factorial \
  --phases peak,trough \
  --horizon 120 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

已有计划可直接复用，不再重新检测周期：

```bash
se-d1-factorial \
  --plan analyses/d1_factorial/d1_factorial_plan.json \
  --output analyses/d1_factorial_rerun \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

## 当前科学主线

1. **D0：** 四资源具有独立外生空间、时间与扩散过程。
2. **D1-A：** 工作记忆、知识、关系与注意力容量可独立遗传、计费和消融。
3. **D1-B：** 固定采集预算下，由遗传 affinity 采样单一资源通道。
4. **D1-C：** 请求流与实现流分离；共享 checkpoint 的 affinity × capacity 因子实验。
5. **D2-A：** 四个表达门控的上下文模块，只向既有四个采集端口发布零和权重残差；不选择动作、不改变同化、不新增物理。

D2-A 是受限探索机制。进入更一般的模块复制、重联或新具身端口前，必须先通过多 seed 长跑和 `neutralize-functional-modules` 配对验证。

## 规范导入

```python
from se.cfg import load_config
from se.env.world import Environment
from se.differentiation import FUNCTIONAL_MODULE_SCHEMA
from se.knowledge import KnowledgeSystem
from se.subjects.graph import CandidateSubjectGraph
from se.runtime.sim import Simulation
```

## 文档

- [项目立项](docs/PROJECT_CHARTER.md)
- [架构与提交边界](docs/ARCHITECTURE.md)
- [项目状态](docs/PROJECT_STATUS.md)
- [科学问题](docs/SCIENTIFIC_ISSUES.md)
- [发行环境与 checkpoint 工作流](docs/v0.39/WORKFLOW_AND_RELEASE_ENV.md)
- [D1 因子结果评估](docs/v0.39/INPUT_D1_FACTORIAL_ASSESSMENT.md)
- [D2-A 机制](docs/v0.39/D2A_CONTEXTUAL_FUNCTIONAL_MODULES.md)
- [D2-A 配对 smoke](docs/v0.39/D2A_PAIRED_SMOKE_REPORT.md)
- [下一轮长跑计划](docs/v0.39/LONG_RUN_PLAN.md)

历史版本详细材料保留在对应发行包中，不重复放入当前源码包。
