# SE v0.35

`SE` 是一个以可审计世界状态、局部交互、遗传策略、动态知识、生态分化和候选主体结构为核心的演化模拟参考实现。

## 命名与目录

本版缩短高频、无歧义路径，同时保留容易误解的领域全称：

```text
subject_evolution → se
domains/environment → env
interfaces/gui → gui
commands → cmd
config.py → cfg.py
runtime/simulation.py → runtime/sim.py
```

以下名称不缩写：`analysis`、`experiments`、`evolution`、`knowledge`、`subjects`、`runtime`。科学配置字段和 schema 也保留完整术语，例如 `environment_schema`，避免把数据协议变成难读缩写。

规范导入示例：

```python
from se.cfg import load_config
from se.env.world import Environment
from se.knowledge import KnowledgeSystem
from se.subjects.graph import CandidateSubjectGraph
from se.runtime.sim import Simulation
```

## 运行

```bash
se \
  --config configs/d0_orthogonal_env_smoke.json \
  --output runs/smoke \
  --backend cpu
```

```bash
se-multi \
  --config configs/mvp_short_d0_orthogonal_env_longrun.json \
  --seeds 10001,10002,10003 \
  --output runs/d0_orthogonal_env_multiseed \
  --backend gpu \
  --until-tick 1500
```

```bash
se-gui \
  --config configs/d0_orthogonal_env_smoke.json \
  --output runs/gui \
  --stream runtime/eco_live.bin \
  --backend cpu
```

也可不安装 console script：

```bash
python -m se --config configs/d0_orthogonal_env_smoke.json --output runs/smoke --backend cpu
python -m se.analysis.parity --config configs/mvp_short_k1_compat.json --output runs/parity
python -m se.env.diversity --config configs/mvp_short_d0_orthogonal_env_longrun.json --output analyses/env_diversity --ticks 600 --sample-period 10
```

## 当前科学主线

1. D0：多维、不可由单一总体充足度解释的环境轴；
2. D1：记忆、知识、关系、传感和储存等弹性容量；
3. D2–D3：固定物理接口内的表达、路由、复制、删除和新功能化；
4. D4：多个生态型的条件性优势与长期共存；
5. D5：真实功能互补和生态依赖之后的社会与高层主体。

D0 的当前主线 schema 为 `orthogonal-four-resource-niche-v1`。高环境维度只证明存在多条选择轴，不证明实体已经发生生态位或功能分化。

## 文档

- [项目立项](docs/PROJECT_CHARTER.md)
- [架构与提交边界](docs/ARCHITECTURE.md)
- [项目状态](docs/PROJECT_STATUS.md)
- [科学问题](docs/SCIENTIFIC_ISSUES.md)
- [分化架构评估](docs/DIFFERENTIATION_ARCHITECTURE_ASSESSMENT.md)
- [v0.35 路径迁移](docs/v0.35/PATH_MIGRATION.md)

历史版本的详细验证材料保留在对应发行包中，不重复放入当前源码包。
