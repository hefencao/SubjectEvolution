# AGENTS.md

本文档适用于本仓库中的所有自动化修改和人工辅助修改。它只规定跨任务长期有效的仓库规则；具体的验证、打包和交付深度由 `docs/WORKFLOW_PROFILES.md` 规定。

## 1. 基线与任务身份

1. 只能使用用户明确指定的项目压缩包或 checkout 作为唯一代码基线。
2. 不得重放旧补丁、复用早期工作树，也不得凭记忆重建缺失代码。
3. 修改前必须声明且只能声明一个 Git 标题：

```text
[TYPE] scope: imperative summary
```

允许的任务类型：

- `[MAIN-EXP]`：已获授权的主线科学实验；
- `[BRANCH-EXP]`：竞争方案或替代方案实验；
- `[PARAM-EXP]`：代码参数探索或参数扫描；
- `[EVOLVE-ENV]`：环境、底物、生态或持续压力相关的演化代码；
- `[EVOLVE-SUBJECT]`：主体能力、主体图、遗传、发育、继承或成本相关的演化代码；
- `[ENGINEERING]`：运行时、性能、测试、打包、工具或重构；
- `[DOC-GOV]`：文档结构、治理规则或任务树维护；
- `[RELEASE]`：仅进行发布组装。

`[BRANCH-EXP]` 必须使用额外 Git 分支。`[PARAM-EXP]` 通常也必须使用额外分支，且不得无声改写已冻结的主线协议。修改环境或主体可演化能力的代码，不得只标记为普通实验。

## 2. 工作流档位选择

开始验证或生成交付物前，必须从 `docs/WORKFLOW_PROFILES.md` 选择一个工作流档位。`AGENTS.md` 不要求每次修改都执行完整发布流程。

- 小型文档、测试或局部代码修复可使用较轻的档位；
- 冻结正式科学结果必须使用科学冻结档位；
- 补丁重放、干净归档、清单和版本标签只属于发布交付档位；
- 不得把小修复无声升级为完整科学或发布周期；
- 当前尚未规定如何自动判断“用户将在本地自行处理、无需生成交付物”，不得凭猜测写成项目规则。

修改 console entry、依赖、包结构或 `pyproject.toml` 时，仍必须执行所选档位规定的环境同步步骤。

## 3. Git 交接合同

每次最终回复都必须给出与所选工作流档位相符的具体 Git 命令。分支名和精确提交标题始终必须提供；只有在本轮作为版本化交付时，才提供合并和标签命令。

分支前缀：

| 类型 | 分支前缀 |
|---|---|
| `[MAIN-EXP]` | `main-exp/` |
| `[BRANCH-EXP]` | `branch-exp/` |
| `[PARAM-EXP]` | `param-exp/` |
| `[EVOLVE-ENV]` | `evolve-env/` |
| `[EVOLVE-SUBJECT]` | `evolve-subject/` |
| `[ENGINEERING]` | `engineering/` |
| `[DOC-GOV]` | `docs/` |
| `[RELEASE]` | `release/` |

交付补丁时不得只写裸文件名。补丁目录由 `se-workspace` 管理，不归 `se-study` 管理。包含该命令的版本应使用：

```bash
git apply --index "$(se-workspace path patch)/<actual-patch-name>"
```

操作员已经配置目录时，不得再次输出新的 `PATCH_DIR=...` 赋值。不得提供破坏性 reset、强制 checkout 或假定远端状态的 pull 命令。

本节是新聊天中 Git 命令格式的长期权威规则；只要先读取本文件，就无需用户重复提醒。

## 4. 类型化任务进度树

`docs/PROJECT_STATUS.md` 必须分别维护以下分支：

- `[MAIN-EXP]`；
- `[BRANCH-EXP]`；
- `[PARAM-EXP]`；
- `[EVOLVE-ENV]`；
- `[EVOLVE-SUBJECT]`；
- `[ENGINEERING]`；
- `[DOC-GOV]`。

每个活动项必须使用 `NEXT`、`ACTIVE`、`BLOCKED`、`PARKED`、`FROZEN` 或 `DONE`。测试、打包和工作区工具不得混入科学主线。

## 5. 文档落点

不得把暂定结果或预期结果写入长期有效的活动文档。

| 内容 | 必须写入的位置 |
|---|---|
| 项目使命与解释边界 | `docs/PROJECT_CHARTER.md` |
| 长期流程与推断规则 | `docs/PROJECT_GOVERNANCE.md` 与本文件 |
| 当前结构合同 | `docs/ARCHITECTURE.md` |
| 当前 Subject Graph VM 机制合同 | `docs/PARTITIONED_SUBJECT_GRAPH_VM.md` 与 `protocols/decisions/` |
| 当前类型化任务树 | `docs/PROJECT_STATUS.md` |
| 当前尚未解决的科学问题 | `docs/SCIENTIFIC_ISSUES.md` |
| 已冻结且已验证的结果 | `docs/results/` |
| 当前迭代设计与工作记录 | `docs/迭代/` |
| 已交付版本变更 | `docs/CHANGELOG.md` |
| 可执行实验身份 | `protocols/decisions/` 与 `studies/*/workflow.toml` |

`PROJECT_CHARTER.md`、`PROJECT_GOVERNANCE.md`、`ARCHITECTURE.md` 和 `PARTITIONED_SUBJECT_GRAPH_VM.md` 不是版本日志。`SCIENTIFIC_ISSUES.md` 只保留未解决问题，`PROJECT_STATUS.md` 只描述当前状态。冻结结果只在 `docs/results/` 汇总一次，不得复制到多份活动文档。

## 6. 科学治理

- 不得预设奖励，也不得给 Objective-Fact 坐标赋固定价值。
- 机制必须有明确成本、消融和共享 checkpoint 对照。
- 普通重复单位是独立 source checkpoint；同一 source 内的实体、窗口、事件、坐标和 tick 不是额外独立样本。
- 必须区分：操纵失败、支持不足、身份或导出失败，以及真实的小效应或路径依赖效应。
- 看到结果后不得放宽阈值、延长暴露、挑选 seed 或修改 horizon；确需修改时必须另立类型化协议。
- 没有单独合同和更强的重复证据，不得授权自动 keep/revert、learned weight、永久 retention 或主体性结论。

## 7. 中文权威与术语规则

中文是活动规范文档的权威解释语言。代码标识、文件名、CLI、协议字段、枚举值、任务类型标签和数学符号保持原文。

首次出现可能有多义性的英文技术词时，应给出中文含义；后续可保留稳定英文标识。不得在同一活动文档中用不同中文词指代同一合同概念。历史快照可保留原文，但必须明确标记为非规范文档。

## 8. 聊天与交付物报告

聊天中只直接报告仍然存在的真实非 GPU 错误。详细验证日志写入所选工作流的证据文件。面向用户的说明应以项目代码、实验设计、数据和结论为中心，不展开例行通过项。
