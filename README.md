# SE v0.37

`SE` 是一个以多维环境、可遗传分化、动态知识和候选主体结构为核心的可审计演化模拟参考实现。

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

分析必须使用当前版本：

```bash
python -m se.analysis.long_run \
  RUN1/evolution_progress.jsonl \
  RUN2/evolution_progress.jsonl \
  RUN3/evolution_progress.jsonl \
  --output analyses/d1b
```

GUI 观察接口：

```bash
se-gui \
  --config configs/d1b_selective_harvest_smoke.json \
  --output runs/gui \
  --stream runtime/eco_live.bin \
  --backend cpu
```

## 当前科学主线

1. **D0：** 四资源具有独立外生空间、时间和扩散过程。
2. **D1-A：** 工作记忆、知识字节、关系槽位和知识注意力容量可独立遗传、计费和消融。
3. **D1-B：** 每次 HARVEST 由遗传资源亲和采样一个资源通道，总请求预算不变；专化以空采和机会成本换取需求分叉。
4. **当前待验证：** 三 seed 长程中环境轴是否保持、容量是否真实选择分化、生态型是否共存。
5. **D2 暂缓：** 在 D1-B 长程和共享 checkpoint 中和通过前，不加入通用表达模块或基因复制。

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
- [D1-B 选择性采集](docs/v0.37/D1B_SELECTIVE_RESOURCE_ACQUISITION.md)
- [上传长跑评估](docs/v0.37/INPUT_D1_LONG_RUN_ASSESSMENT.md)
- [D1-B 配对 smoke](docs/v0.37/D1B_PAIRED_SMOKE_REPORT.md)
- [下一轮长跑计划](docs/v0.37/LONG_RUN_PLAN.md)

历史版本详细材料保留在对应发行包中，不重复放入当前源码包。
