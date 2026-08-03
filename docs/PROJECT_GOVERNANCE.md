# SubjectEvolution 项目治理规则

职责：规定跨版本长期有效的任务选择、执行、冻结、记录和交接规则。具体命令深度由 `docs/WORKFLOW_PROFILES.md` 管理；仓库级代理规则由 `AGENTS.md` 汇总。

## 1. 每轮治理检查

每次迭代都必须进行一次轻量治理检查：

1. **预期检查**：观察结果是否偏离预注册预期？
2. **根因检查**：偏离来自操纵、支持、身份/导出、观测覆盖、source 健康，还是实际科学效应？
3. **任务检查**：当前任务应继续、停在前置条件，还是重新分类？
4. **原则检查**：本轮是否发现新的长期规则，或修改了现有规则？
5. **文档检查**：是否仍有长期规则只存在于聊天或单轮迭代记录中？

意外结果不自动意味着要改机制。前置资格失败也不等于下游假设失败。

## 2. 类型化工作与分支纪律

每项修改必须有且只有一个主要类型和 Git 标题：

```text
[TYPE] scope: imperative summary
```

主线科学实验、替代分支实验、参数探索、环境演化代码、主体能力演化代码、工程修改、文档治理和发布组装是不同工作类别。改变环境或可演化主体能力的代码，不能隐藏在普通实验标签中。

竞争实验和参数探索必须使用独立分支，除非记录了明确例外原因。探索工作不得无声改写已冻结的主线协议。

## 3. 遗传或社会推断前的环境成熟度

环境构建先于筛选和社会解释。一个 source 要支持这些结论，必须通过预先声明的相关门：

- 可行种群与周转；
- 足够代际深度与创始者替换；
- 物理异质性与机会结构；
- 相关材料或信息依赖；
- 覆盖最长已配置外部强迫周期的观测范围。

单个 source 可用于调试共享环境参数，但不能授权冻结的遗传、生态、社会或主体性结论。

深度瓶颈后的种群反弹不能单独恢复 source 资格；还必须检查谱系广度和替换程度。

## 4. 能力开发优先检查集成系统

当健康底物中已存在多个机制和环境轴时，应先研究集成系统，不得自动为每个基因分别创建环境、候选台账或成对实验。

应先用有限的多代 panel 识别：哪些能力不存在、未使用、成本错误、环境不支持，或在成熟前丢失。只有获得这些证据后，才修改共享接口、发育时程、成本预算或物理机会。

健康门只用于确认载体底物合格，不用于选择偏好能力，也不证明适应。

## 5. 操纵、暴露与观测

因果操纵必须证明实际发生。必要检查可包括：

- 预定 target 和 route 确实改变；
- control 预留了匹配预算但没有改变状态；
- branch 随机流和 source 身份保持对齐；
- 实际 dose 与 duration 符合声明；
- rollback 或 finalization 按要求完成；
- 观测窗口覆盖了可能的下游效应。

暴露研究必须区分：

1. live-ledger dose；
2. 共同 evaluation support；
3. observation coverage。

如果改变 exposure 会改变导出前完成的窗口集合，则 rollback-complete window 不能在没有共同支持修正时作为主要传播估计器。

## 6. 重复与推断身份

普通主要重复单位是独立 source checkpoint，或其他预注册的独立世界历史。同一 source 内的事件、实体、窗口、坐标和 tick 是相关证据。

冻结推断必须明确绑定：

- 归一化配置；
- source checkpoint 与权威状态 hash；
- branch role 与 paired family；
- random-stream policy；
- manipulation policy；
- export schema 与 finalization 状态；
- assessment 版本与输入 checksum。

研究可以在前置门停止。此时下游预测状态是“未测试”，而不是“获得支持”或“被反驳”。

## 7. 候选集合与 portfolio 边界

探索分析可以发现候选机制、参数区域、source family 或测量方法，但不得在同一数据上选择候选后又宣称独立确认。

存在多个候选时必须：

- 记录完整候选集合和选择规则；
- 分开 calibration source 与 inference source；
- 在独立 panel 前冻结所选候选；
- 在证据包中保留失败和零结果 source；
- 不得把单个成功坐标、seed 或 branch 提升为通用机制结论。

## 8. Subject Graph VM 治理

### 8.1 架构先验与具体认知必须分开

项目可以固定有限区域、路由阶段、通用算子、状态容量、eligibility、provenance 和成本；不得把语义化收益台账、固定 reward、trust、hostility、group identity、knowledge value 或角色专属 policy 作为答案编码进去。

### 8.2 单一路由所有权

当 Subject Graph VM 拥有可选的主路径 action-residual 时，legacy knowledge residual、latent router、quantized working-memory 和 sparse-selection route 不得作为竞争所有者同时执行。旧实现可以保留用于旧 checkpoint、消融和固定认知基线，但不能自动迁入 Subject VM 身份。

### 8.3 Bootstrap 机制

固定 bootstrap attention、readout 和 addressing 只是工程塑形工具。其 score、rank、margin、selected identity 或 update route 没有内在价值含义。历史分析分箱不得混同为 runtime comparator 语义。

### 8.4 临时写入边界

临时写入必须具有有限 target family、明确 delta 上限、control reservation、transaction identity、later-tick visibility、rollback 和 export-boundary finalization。

没有独立协议和更强重复证据，不得启用自动 keep/revert、learned weight、adaptive exposure 或永久 retention。

## 9. 冻结结果与工作区边界

生成的分析、checkpoint、结果包、补丁目录和操作员工作区配置默认保留在项目树外；只有紧凑且明确获准的冻结产物可以进入跟踪树。

冻结结果必须：

- 用 checksum 和 lineage 绑定输入；
- 包含足以复现完整运行链的元数据；
- 包含零结果、失败和提前停止的 branch；
- 逐组件汇总证据，不得隐藏标量化；
- 区分暂定解释与获授权结论。

`se-workspace` 管理本地 result 和 patch 目录。study runner 只读取这些设置，不拥有它们。

## 10. 声明式研究执行

正式研究使用版本化的声明式 workflow。参数必须有类型、默认值和说明。执行前必须能够检查渲染后的精确 argv，调用时不得无声经过 shell。

workflow 必须记录前置门、source panel、branch plan、assessment、打包步骤和预期输出。看到结果后修改 workflow，必须建立新的类型化协议。

## 11. 文档权威

活动文档职责不得重叠：

| 内容 | 权威位置 |
|---|---|
| 项目使命与解释限制 | `PROJECT_CHARTER.md` |
| 长期流程与推断规则 | `PROJECT_GOVERNANCE.md` 与 `AGENTS.md` |
| 当前结构架构 | `ARCHITECTURE.md` |
| 当前 Subject Graph VM 机制合同 | `PARTITIONED_SUBJECT_GRAPH_VM.md` |
| 当前类型化任务树 | `PROJECT_STATUS.md` |
| 当前未解决科学问题 | `SCIENTIFIC_ISSUES.md` |
| 已冻结且验证的科学结果 | `docs/results/` |
| 当前迭代计划和工作记录 | `docs/迭代/` |
| 可执行实验身份 | `protocols/decisions/` 与 `studies/*/workflow.toml` |
| 已交付版本历史 | `CHANGELOG.md` |

暂定或预期结果只能留在分析输出或当前迭代记录中。Architecture、Charter、Governance、Status 和 Scientific Issues 都不是版本日志。

结果冻结后，只在相应 result ledger 中总结一次完整运行链，不得把同一叙事复制到多个活动文档。

## 12. 工作流深度与交接

验证与交付深度由 `docs/WORKFLOW_PROFILES.md` 选择：

- `SCOPED-FIX`：局部修复；
- `STANDARD-CODE`：共享代码或公共接口变化；
- `SCIENTIFIC-FREEZE`：正式实验执行和结果冻结；
- `RELEASE-HANDOFF`：归档、补丁、重放和可迁移性证据。

例行通过项写入证据文件。聊天只报告仍然存在的真实非 GPU 错误、科学结论和用户要求的交接命令。
