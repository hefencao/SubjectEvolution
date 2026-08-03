# SubjectEvolution 当前架构

## 1. 职责与权威

本文档只描述项目**当前仍然有效的结构边界**。它不是版本日志、实验报告、任务清单或科学问题列表。

只有跨越引入它的单轮迭代后仍然成立的结构合同才应写在这里。冻结实验结论写入 `docs/results/`；未解决科学问题写入 `docs/SCIENTIFIC_ISSUES.md`；当前工作写入 `docs/PROJECT_STATUS.md`；版本交付历史写入 `docs/CHANGELOG.md`。

核心设计目标是在不预设 reward、人类社会角色或 Objective-Fact 固定语义价值的前提下，支持类似主体的内部组织进行模拟、干预和演化研究。

## 2. 系统依赖图

```text
配置与身份合同
        ↓
环境 / 生理 / 演化 / 分化 / 知识 / 主体
        ↓
运行时编排与 checkpoint 所有权
        ↓
命令行接口与只观察/控制的 GUI bridge

分析 / 实验 → 运行时与领域读取接口
运行时与领域 ✕→ 分析、实验或 GUI policy
```

主要 Python 包布局：

```text
src/se/
├── analysis/          外部、只读或运行后评估
├── cmd/               console entry point
├── differentiation/   可遗传分化机制
├── env/               世界字段与结算
├── evolution/         变异、繁殖与筛选基础设施
├── experiments/       声明式 branch 与 study runner
├── gui/               Python 观察/控制 bridge
├── knowledge/         知识副本转移与验证机制
├── runtime/           权威模拟编排
├── subject_vm/        统一主体图运行时与 trace 状态
├── subjects/          主体所有权与生命周期
└── cfg.py             归一化配置合同
```

独立原生工作区 `src/gui/` 使用自身工具链构建，不进入 `make test` 使用的 Python release-freshness 指纹。`src/se/gui/` 仍是普通 Python 产品代码，继续处于测试和发布新鲜度边界内。

## 3. 运行时所有权

### 3.1 权威世界状态

runtime 拥有 tick 顺序、实体生命周期、随机流推进、checkpoint 边界、branch 身份和最终报告物化。领域系统可以提出 intent 或局部更新，但不得绕过 runtime 的结算顺序独立提交世界状态。

请求和实际实现必须分开：

```text
policy / graph 输出
    → requested action 或 requested resource vector
    → 可行性、竞争与世界结算
    → realized action、transfer、resource 与 objective event
```

requested value 是因果意图，realized value 是受约束结果。分析或信用归因不得用后者替代前者。

### 3.2 Backend 合同

- 高层默认值是 `auto`，并必须记录实际解析到的 backend；
- `cpu` 是权威语义参考；
- 加速 backend 必须保持 checkpoint 权威状态和报告边界；
- parity 是验证边界，不是科学干预；
- allocator cache、编译产物和设备可用性都是工程因素，不得解释为生物或认知效应。

### 3.3 报告与 checkpoint 物化

报告和 checkpoint 导出必须在每个 tick 看到同一个权威物化状态。设备镜像可在内部延迟同步，但最终 summary、checkpoint、branch export 和 reproducibility assessment 必须标识物化 tick 与来源。

## 4. 配置、checkpoint 与 branch 身份

配置归一化属于实验身份。研究必须绑定：

- normalized configuration hash；
- source checkpoint 文件与权威 state hash；
- source tick 与 final tick；
- 明确 branch role 与 intervention identity；
- random-stream ownership；
- 允许的配置差异；
- export 与 assessment checksum。

branch runner 只能改变协议声明的因素。无关配置变化、替换 source、事后延长 horizon 或缺失 lineage 字段都会使 paired interpretation 失效。

checkpoint 兼容层只有通过明确的版本化默认值，才能补建旧版本缺失字段。恢复 checkpoint 时不得无声启用新机制，也不得把回收 entity row 的状态继承给新实体。

## 5. 环境与具身底物

世界提供空间持续的资源、地形、信号和材料约束。Subject 机制只能通过现有 action 和 settlement 接口作用于世界，不得直接获得角色奖励。

当前稳定边界包括：

- 多资源通道分别拥有 request、availability、storage、conversion 与 conservation 路径；
- 可遗传 capacity 和 affinity 支付明确结构成本或使用成本；
- 空间资源地理、terrain resistance、signal openness 与局部竞争；
- 延迟 raw-resource metabolism 和 residual-material settlement；
- 有界 physiology、repair、fatigue 与 messenger state；
- source-health gate：灾难性人口坍塌后，阻止普通机制解释继续进行。

环境多样性和主体能力属于演化代码，而不是普通实验参数。对它们的修改必须在任务树和 Git 标题中使用独立类型。

## 6. Legacy 社会与知识基线

material-interest 与 transferred-knowledge 机制保留为固定认知比较基线。它们可以产生延迟且可审计的证据，但不拥有 Subject VM 的主 action-residual 路径。

稳定边界：

- material giving/receiving 与 knowledge verification 在不同通道结算；
- transferred-copy attribution 使用稳定 source identity；
- 证据不得附着到回收后复用的 entity row；
- 缺失历史身份时保留为 orphan，不得重新指派；
- group detection 默认为观察结果，除非另有 Epoch 合同授予控制权。

这些基线不得扩展为第二套竞争主体网络。

## 7. 统一 Subject Graph VM

### 7.1 所有权与拓扑

Subject VM 是一个由稳定主体拥有的、内部带分区的统一 node/edge graph。区域可以提供初始塑形偏置，但不是彼此独立的语义网络，也不构成对认知、角色、利益或价值的证据。

当前图使用固定 topology 和有限状态。topology mutation、region-capacity evolution、developmental expression、migration 与永久 retention 均未获授权。

### 7.2 Activation 边界

activation adapter 读取获准的客观输入端口，按确定性阶段顺序执行通用 node/edge operator，并向现有 action 接口发布有界 residual。action system 仍是 feasibility mask、categorical sampling、intent 与世界结算的唯一所有者。

同一 phase 内的数组顺序不得产生隐藏的零延迟依赖。delayed edge 只能读取明确保留的先前状态。

### 7.3 长期事件 trace

长期 trace 只保存固定宽度 continuous token 和有限的 post-commit Objective-Fact。它不保存完整执行路径、activation mask、全部 node/edge 身份历史或人类语义标签。

Objective-Fact 是测量值，不是 reward。各坐标保持分离，默认不形成标量价值。

### 7.4 Local eligibility 与 delayed association

短期 local eligibility 只能由实际发生的有界 node output 或 edge transmission 写入，并受 graph flag 与 gate 控制。其正负号是计算方向，不是事件效价。

delayed association 是有限 bootstrap addressing 机制：

- candidate 是同一稳定主体历史中、位于明确 delay 范围内的更早事件；
- normalized visible-token similarity 控制 admission 与 ranking；
- 当前固定 bootstrap 最多使用两个可见坐标和有限 candidate 数；
- 确定性的 latest/top-1 排序只是一项工程基线；
- association 记录寻址诊断，不表示因果真相或价值。

固定 bootstrap 的作用是让早期图塑形可诊断，不代表通用 attention 或最终 general allocator。

### 7.5 参数提案与临时 transaction

graph-controlled readout 形成有界 parameter-family proposal。有效 proposal 必须绑定到精确且稳定的 node/edge target，通过安全复核，并在任何 live write 前进入 atomic shadow transaction。

guarded live write 必须显式启用、具有有限时长并受 rollback 约束。live ledger 记录 transaction identity、target、family、bounded delta、pre/post value、commit tick、rollback due tick 与 finalization status。read-only control 预留匹配预算但不改变参数。

永久 keep/revert、learned weighting、scalar reward 与 retention 不属于当前 runtime。

### 7.6 仅用于实验的 alignment policy

trace runtime 为 subject-time alignment 研究提供明确的 experiment-only association-coordinate policy。identity 与 cyclic-donor 模式共用同一稳定 sort/copy 实现，并精确保留每个 tick 的 float32 坐标 multiset。policy、port 和 origin tick 都必须进入 branch identity。

这些 policy 只用于检验因果路由，不定义生产级 attention 机制。

## 8. 证据管线

证据栈刻意位于 runtime learning path 之外：

```text
共享 source checkpoint
    → 声明的 paired 或 multi-arm branch plan
    → guarded-live / read-only-control 执行
    → 验证 branch 与 lineage 后导出
    → integrity assessment
    → source-balanced component reproducibility assessment
    → frozen result ledger
```

普通最高重复单位是独立 source checkpoint，而不是该 source 内的实体、窗口、事件或坐标数量。

assessment 必须保留：

- paired 与 unpaired support；
- rollback 和 pending-write 状态；
- fact clipping 与 evaluation-cost 检查；
- 不含隐藏标量化的组件级事实；
- source-balanced aggregation；
- 对 manipulation failure、support failure、identity error 与真实小效应/路径依赖效应的精确区分。

更长干预必须分别证明 realized dose、固定共同 evaluation support 和充分 observation coverage。

## 9. Study 与发布工具

study 由 `workflow.toml` 声明。每个参数都有类型、默认值和说明。`se-study show` 渲染精确 argv，`se-study run` 不经过 shell 直接调用。结果打包必须是明确 workflow step。

项目外操作员路径由 `se-workspace` 管理；它读取和写入被忽略的 `.se-workspace.toml`。`se-workspace config` 设置 result 和 patch 目录；`se-workspace path result|patch` 为脚本与 Git 交接输出一个已配置路径。study runner 只消费 result-directory 设置，不拥有工作区配置。

验证和交付深度由 `docs/WORKFLOW_PROFILES.md` 选择。小修复不自动进入发布流程；公共 CLI、package 或共享 runtime 变更使用标准代码档位；科学冻结使用科学档位；补丁和归档检查只在发布交付时执行。

release packaging、patch replay、archive governance 与 isolated wheel/sdist 检查只验证可迁移性，不改变科学结论。

## 10. 文档边界

| 文档 | 应包含 | 不得包含 |
|---|---|---|
| `PROJECT_CHARTER.md` | 长期使命、范围与解释边界 | 当前任务状态、逐版本结果 |
| `PROJECT_GOVERNANCE.md` | 长期流程与推断规则 | 原始实验叙事、版本日志 |
| `ARCHITECTURE.md` | 当前结构合同 | 逐版本结果、任务队列、暂定结论 |
| `PARTITIONED_SUBJECT_GRAPH_VM.md` | 当前 VM 机制与安全合同 | 按 Stage 排列的结果历史 |
| `PROJECT_STATUS.md` | 当前类型化任务树与冻结前沿 | Stage-by-Stage 历史、测试报告 |
| `SCIENTIFIC_ISSUES.md` | 当前未解决科学问题 | 发布说明、已解决历史、工程缺陷 |
| `docs/results/` | 已冻结且验证的结果台账 | 暂定解释 |
| `docs/迭代/` | 当前迭代设计、工作记录和最终说明 | 跨版本权威规则 |
| `CHANGELOG.md` | 已交付版本变化 | 科学待办列表 |

Subject VM 的详细协议和机制语义由 `docs/PARTITIONED_SUBJECT_GRAPH_VM.md` 与 `protocols/decisions/` 管理。
