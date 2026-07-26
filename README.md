# SE v0.36

`SE` 是一个以可审计世界状态、多维环境、可遗传分化、动态知识和候选主体结构为核心的演化模拟参考实现。

## 运行

安装后：

```bash
se --config configs/d1_elastic_capacities_smoke.json --output runs/d1_smoke --backend cpu
```

D1 三 seed 主线：

```bash
se-multi \
  --config configs/mvp_short_d1_elastic_capacities_longrun.json \
  --seeds 10001,10002,10003 \
  --output runs/d1_elastic_capacities_multiseed \
  --backend gpu \
  --until-tick 1500
```

也可直接使用模块入口：

```bash
python -m se --config configs/d1_elastic_capacities_smoke.json --output runs/d1_smoke --backend cpu
python -m se.analysis.protocol_audit --config configs/mvp_short_d1_elastic_capacities_longrun.json --output analyses/d1_protocol
python -m se.analysis.long_run RUN1/evolution_progress.jsonl RUN2/evolution_progress.jsonl RUN3/evolution_progress.jsonl --output analyses/d1
```

GUI 观察接口：

```bash
se-gui \
  --config configs/d1_elastic_capacities_smoke.json \
  --output runs/gui \
  --stream runtime/eco_live.bin \
  --backend cpu
```

## 当前科学主线

1. **D0 已完成机制实现：** `orthogonal-four-resource-niche-v1` 提供相互独立的空间、时间和扩散环境轴。
2. **D1-A 已完成机制实现：** `inherited-elastic-capacities-v1` 使工作记忆、知识字节、关系槽位和知识注意力容量独立遗传，并支付维护与发育成本。
3. **当前待验证：** D1 三 seed 长程中是否出现真实选择响应、环境条件性容量优势和多个可持续生态型。
4. **D2 暂不启动：** 在 D1 的实际使用与因果作用通过前，不加入通用表达模块或基因复制。

D1 不预设“聪明型”“社交型”等角色。容量只改变现有机制的可用规模；生态角色必须由长期环境使用和延续结果识别。

## 规范导入

```python
from se.cfg import load_config
from se.env.world import Environment
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
- [D1 弹性容量](docs/v0.36/D1_ELASTIC_CAPACITIES.md)
- [D1 长跑计划](docs/v0.36/LONG_RUN_PLAN.md)
- [D1 配对 smoke](docs/v0.36/D1_PAIRED_SMOKE_REPORT.md)

历史版本的详细验证材料保留在对应发行包中，不重复放入当前源码包。
