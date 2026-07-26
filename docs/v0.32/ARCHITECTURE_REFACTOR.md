# v0.32 架构重构

## 目标

本轮只重排代码责任与依赖边界，不修改世界规则、配置默认值、随机键、提交顺序、日志内容或 checkpoint 语义。

原目录把世界实现、分析 CLI、自然事件实验、环境、演化、主体和知识实现平铺在 `subject_evolution/` 下；`simulation.py` 达 5034 行，`knowledge.py` 达 3118 行。该结构使世界核心与离线工具互相可见，也使 checkpoint、报告和实验干预继续挤入单一 `Simulation` 类。

## 新目录

```text
subject_evolution/
├── runtime/
│   ├── state.py          # EntityState、StepStats、周期位置规范化
│   ├── simulation.py     # Simulation 初始化、世界 step 与 run
│   ├── checkpointing.py  # trusted checkpoint、restore、clone
│   ├── experiments.py    # intervention、fixed cohort、trajectory hook
│   └── reporting.py      # manifest、scientific validity、progress、metrics
├── domains/
│   ├── environment/      # world/process/GPU/atlas/niche/spatial/local stress
│   ├── evolution/        # lifecycle 与 evolution progress
│   ├── subjects/         # subject graph、social、control、succession
│   └── knowledge/
│       ├── types.py      # immutable plans 与 StepStats
│       ├── storage.py    # KnowledgeCatalog / KnowledgeArena
│       ├── system.py     # lifecycle orchestration
│       ├── logging.py    # 高容量审计日志
│       ├── diagnostics.py
│       └── policy/latent/working-memory/routing 子模块
├── analysis/             # long-run、protocol、parity、result audit/synthesis
├── experiments/          # counterfactual 与 natural-event 执行
└── compatibility facades # 原顶层模块路径
```

## 大文件拆分结果

| 原实现 | v0.31 | v0.32 主实现 |
|---|---:|---:|
| `simulation.py` | 5034 行 | core engine 2203；reporting 1833；checkpoint 676；experiments 420；state 358 |
| `knowledge.py` | 3118 行 | system 1341；diagnostics 664；logging 439；types 435；storage 361 |
| 顶层兼容 `simulation.py` | 5034 行 | 41 行 |
| 顶层兼容 `knowledge.py` | 3118 行 | 4 行 |

`runtime/reporting.py` 仍较大，但它已不在每 tick 的世界核心文件内。下一次需要继续拆分时，应按 manifest/scientific-validity/metrics 三种发布协议分开，而不是重新塞回引擎。

## 兼容策略

原模块名继续存在，例如：

```python
from subject_evolution.simulation import Simulation
from subject_evolution.knowledge import KnowledgeSystem
from subject_evolution.environment import Environment
```

这些模块成为 facade，并转发实现命名空间。facade 还转发 monkey-patch 写入，因此测试和外部工具对 `subject_evolution.simulation.resolve_backend`、`normal`、自然事件 `_run_branch` 等历史 patch 点仍有效。

`EntityState` 和 `StepStats` 保留历史 pickle module identity，v0.31 trusted checkpoint 可以由 v0.32 加载。

## 依赖规则

1. `runtime` 可以依赖 domain 和 infrastructure，但 analysis 不得被世界循环调用。
2. `analysis` 和 `experiments` 可以依赖兼容 facade 或 domain API；它们不能获得额外世界写权限。
3. domain 模块不得导入自然事件执行器或 long-run analyzer。
4. 新实现优先放入分层 package；顶层只保留稳定 facade、CLI 入口和基础 infrastructure。
5. checkpoint 中的权威 state schema 与 Python 文件位置分离；移动文件不得静默改变世界状态字段。

## 仍未拆分的边界

- `Simulation.step()` 仍约 1200 行。下一次拆分应先引入显式 `StepContext` 和 phase result types，再按 observation、control、resolution、commit、lifecycle 分相；不应用简单剪贴制造隐式共享局部变量。
- `runtime/reporting.py` 仍包含多种发布协议。
- `domains/knowledge/latent.py`、`analysis/long_run.py` 等仍超过 1300 行，但它们已脱离世界主循环。
- 配置仍集中在 `config.py`。在 schema 数量继续增长前，应拆成 dataclass 定义、解析、验证和迁移四层。
