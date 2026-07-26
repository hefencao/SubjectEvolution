# SE v0.38

`SE` 是一个围绕多维环境、可遗传分化、动态知识和候选主体结构构建的可审计演化模拟参考实现。

## 运行

```bash
se \
  --config configs/d1b_selective_harvest_smoke.json \
  --output runs/d1b_smoke \
  --backend cpu
```

D1-B 三 seed 主线：

```bash
se-multi \
  --config configs/mvp_short_d1b_selective_harvest_longrun.json \
  --seeds 10001,10002,10003 \
  --output runs/d1b_selective_harvest_multiseed \
  --backend gpu \
  --until-tick 1500
```

当前分析器会区分采集**请求量**与环境约束后的**实际采得量**，并分别报告总规模和通道组成：

```bash
python -m se.analysis.long_run \
  runs/d1b_selective_harvest_multiseed/seed_10001/evolution_progress.jsonl \
  runs/d1b_selective_harvest_multiseed/seed_10002/evolution_progress.jsonl \
  runs/d1b_selective_harvest_multiseed/seed_10003/evolution_progress.jsonl \
  --output analyses/d1b_v038
```

D1 亲和表达 × 容量表达四分支配对实验：

```bash
se-d1-factorial \
  --run-dir runs/d1b_selective_harvest_multiseed/seed_10001 \
  --run-dir runs/d1b_selective_harvest_multiseed/seed_10002 \
  --run-dir runs/d1b_selective_harvest_multiseed/seed_10003 \
  --output analyses/d1_factorial \
  --phases peak,trough \
  --horizon 120 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

## 发行包验证

普通源码测试可能被 `PYTHONPATH=src`、旧 editable install 或当前工作目录掩盖。每次候选发行应执行：

```bash
make release-check PREVIOUS_WHEEL=/path/to/se_mvp-0.37.0-py3-none-any.whl
```

该流程在一次性 venv 中：

1. 生成 sdist；
2. 从 sdist 构建 wheel；
3. 先安装旧 wheel，再 `--force-reinstall` 候选 wheel；
4. 清空 `PYTHONPATH` 和 user site，并切换到源码树外；
5. 确认 `se.__file__` 位于候选 venv；
6. 导入全部已安装模块，执行 `pip check`；
7. 验证 `se`、`se-multi`、`se-gui`、`se-d1-factorial`；
8. 使用复制到源码树外的 config 完成短程运行。

严格依赖隔离可使用：

```bash
python scripts/verify_dist.py \
  --project . \
  --strict \
  --wheelhouse /path/to/offline-wheelhouse
```

## 当前科学主线

1. **D0：** 四资源具有独立外生空间、时间和扩散过程。
2. **D1-A：** 工作记忆、知识字节、关系槽位和知识注意力容量可独立遗传、计费和消融。
3. **D1-B：** 每次 HARVEST 由遗传资源亲和采样一个资源通道；总请求预算不变，专化承担空采和机会成本。
4. **D1-C：** 显式记录请求/实现资源流，并用共享 checkpoint 的 affinity × capacity 四分支实验识别局部表达效应。
5. **D2 暂缓：** 在请求组成和配对效应跨 seed 可重复之前，不加入通用表达模块或基因复制。

## 规范导入

```python
from se.cfg import load_config
from se.env.world import Environment
from se.env.niches import harvest_request_rates
from se.differentiation import CapacityPhenotype
from se.knowledge import KnowledgeSystem
from se.subjects.graph import CandidateSubjectGraph
from se.runtime.sim import Simulation
```

## 文档

- [项目立项](docs/PROJECT_CHARTER.md)
- [架构与提交边界](docs/ARCHITECTURE.md)
- [项目状态](docs/PROJECT_STATUS.md)
- [科学问题](docs/SCIENTIFIC_ISSUES.md)
- [D1-C 请求组成与因子实验](docs/v0.38/D1C_REQUEST_COMPOSITION_AND_FACTORIAL.md)
- [隔离 wheel 验证](docs/v0.38/RELEASE_VALIDATION.md)
- [下一轮长跑计划](docs/v0.38/LONG_RUN_PLAN.md)

历史版本详细材料保留在对应发行包中，不重复放入当前源码包。
