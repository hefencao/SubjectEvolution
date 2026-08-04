# 分区式 Subject Graph VM

状态：**当前机制合同**
合同代次：**v1**
仓库审查版本：**v0.166**

本文档定义当前有效的 Subject Graph VM 架构和安全边界。它不是版本日志，也不是实验结果台账。Stage 3C 的历史结论由 `docs/results/SUBJECT_VM_STAGE3C_RESULTS.md` 汇总；可执行细节由 `protocols/decisions/` 管理。

## 1. 架构决策

SubjectEvolution 使用一个内部带分区、可演化的统一主体图，而不是为每个被命名的收益、记忆、信任、知识或 policy 功能分别创建程序员预设的台账或网络。

VM 提供：

- 一套统一的 node 与 edge 身份系统；
- 具有初始偏置的计算区域；
- 一套共享路由底物；
- 分离的 activation 与 delayed-update phase；
- 有界的 provenance、token、eligibility 与 transaction 状态；
- 不内置 reward、trust、hostility、knowledge value、social role 或 group preference。

项目可以预设通用认知架构，使长时程组织在计算上可达；不得预设占据该架构的具体认知内容。

## 2. 范围与非目标

VM 用于研究持续内部组织能否出现并产生因果影响。它不负责：

- 定义通用 utility 或 reward；
- 为 Objective-Fact 赋主观效价；
- 定义朋友、敌人、角色、忠诚或群体成员身份；
- 强制 actor-critic 或其他命名认知分解；
- 把归因、记忆、利益与决策永久拆成独立服务；
- 取代观察者侧的延续与反事实分析；
- 仅凭 score geometry 授权 learning、retention 或主体性。

D1-X/Y 的语义化台账继续作为固定认知比较基线和兼容性 fixture，不是主要科学模型。

## 3. 一个图，多个偏置区域

区域是发育和调度先验。它们共享图身份，未来可以重叠、改变容量或交换功能。

### 3.1 快速感觉—运动区域

- 按 policy cadence 更新；
- 读取即时 observation 与 body state；
- 支持最小、角色中立的 action path；
- 持续性低且成本有界；
- 可以贡献 action potential。

### 3.2 持续状态区域

- 跨 tick 保留有界内部状态；
- 支持配置化 decay 与 overwrite；
- 支付容量和持续时长成本；
- 可通过共享 router 读写。

### 3.3 延迟关联区域

- 只在世界结算后观察 Objective-Fact；
- 可以比较后续事实与更早的 graph-produced token；
- 可以对仍然存活的 local eligibility 提出 modulation；
- 不得改变其后果尚未发生的动作。

### 3.4 综合驱动区域

- 组合即时状态、保留状态与延迟状态；
- 可以影响 action-channel potential；
- 允许 recurrence，以及类似利益和类似决策的组织发生重叠；
- 不接收特权 reward 输入。

区域名称只是工程标签，不是认知功能证据。

## 4. 统一 node、edge 与存储合同

### 4.1 Node 合同

已表达 node 具有以下有界且版本化字段：

- subject-lineage state 内的稳定 node identity；
- region 与 update schedule；
- 角色中立 operator；
- expression gate 与 activation gate；
- internal state 与 retention；
- 可选 trace readout port 与 gate；
- plasticity participation；
- structural、execution 与 retention cost。

### 4.2 Edge 合同

已表达 edge 具有以下有界字段：

- source node 或获准 external port；
- target node 或获准 output port；
- weight 或 gate；
- delay、bandwidth 与 persistence；
- activation phase 与 delayed phase 权限；
- eligibility/plasticity participation；
- structural cost 与 use cost。

memory、knowledge、action 与 latent computation 不得各自发明互不兼容的 edge identity。

### 4.3 存储与生命周期

VM 使用固定容量存储，并显式记录 occupancy 与稳定 subject binding。生命周期操作必须处理：

- 初始化与 disabled null state；
- entity birth、death、compaction 与 slot reuse；
- 声明位置上的结构继承与动态状态重置；
- checkpoint save/restore 与 clone；
- regional branch 构建；
- retired row 的确定性清除。

world history、graph token history、local eligibility、subject-owned memory 与 analysis output 是彼此独立的容量。

### 4.4 ThoughtEvent 与最小前向 recall

统一 ThoughtEvent arena 保存 graph-produced pre-action token 和稳定 event identity。启用 T3 时，runtime 可以为每个主体确定性选择最近一个严格早于当前 tick 的 retained ThoughtEvent，并通过最多一条声明式 `node_recall_port`/`node_recall_gate` ingress 进入普通 node accumulator。

该路径：

- 默认关闭；
- 不读取同 tick 新事件；
- 不拥有 query network、随机检索、temperature 或固定认知角色；
- 不直接回灌 action logits、Objective-Fact 或 value；
- 将实际 selected event 记录为 child ThoughtEvent 的 parent DAG edge；
- 启用时属于 configuration、checkpoint、clone 与 branch identity；
- 成本只记录搜索、读取、ingress 和 parent-link 计数，不自动影响 energy 或 retention。

当前 T3 fixed-bootstrap ingress 位于 readout-only node，不构成长期规范拓扑，也不证明思维链、语义记忆或延迟信息效用。

## 5. 所有权与依赖方向

现有 action strategy 仍是最小可遗传感觉—运动基线。feasibility mask、categorical sampling、intent 与 world settlement 仍由物理 action 系统权威拥有。

启用时，Subject VM 是可选主路径 action-potential residual 的唯一所有者。legacy knowledge residual、latent router、quantized working-memory 与 sparse-selection route 可以为旧 checkpoint 和基线保留，但不得作为竞争 residual owner 同时执行。

knowledge provenance 仍是客观外部 store。functional module 仍是具身机制。candidate-subject graph 与 group graph 仍是观察结果。它们都不得被整体复制进 Subject VM 身份或状态。

不得自动把旧 semantic gene、memory coordinate 或 benefit ledger 转换为 Subject VM node/edge。

## 6. 因果执行阶段

### 6.1 激活（Activation）

```text
客观 input port 与保留 graph state
→ 按 schedule 执行 graph activation
→ 有界 node/edge transmission
→ action-potential output port
→ 现有 policy mask 与 sampling
→ 世界执行与结算
```

零延迟 routing 只能指向允许的更早 activation phase。其他 recurrence 必须读取上一个保留状态或明确 delayed edge。

### 6.2 客观事件轨迹（Objective trace）

结算后，runtime 可以追加一条有界 event record，包含：

- event identity 与 tick identity；
- 参与者的稳定 subject identity；
- 已执行 action 与物理 target；
- Objective-Fact 的 pre/post 值；
- 实际 content 或 signal provenance；
- graph 产生的有界 continuous token；
- 由物理过程定义的 parent/source event reference。

trace 不保存完整 graph 执行路径。

### 6.3 局部资格痕迹（Local eligibility）

graph-owned node/edge eligibility 只能由实际发生的有界 activation 或 transmission 产生。其 decay、expiry、checkpoint、clone 和 clear 都必须有明确生命周期规则。eligibility 不复制进长期 event history，也没有固定价值含义。

### 6.4 延迟关联（Delayed association）

后续 event 可以从同一稳定 subject history 中请求一个有界历史 candidate。candidate admission 由声明的 delay、nonzero-token、threshold 与 control-port 规则控制；assignment 可以为空。

association 只记录 identity、tick、delay 与 similarity，不表示因果性、正确性、价值或语义等价。

### 6.5 调制提案（Modulation proposal）

只有仍存在合格 local carrier 时，有界 delayed association 才能提出 target family、carrier 与 signed delta。proposal generation 与 parameter update 必须分开。Objective-Fact 保持逐组件，不转换为 reward。

### 6.6 影子事务（Shadow transaction）与受控实时写入（guarded live write）

shadow transaction 在不改变权威参数的情况下验证 target resolution、compare-and-swap 前置条件、delta bound、branch identity 与 rollback。

guarded live write 还要求：显式 opt-in、匹配的 read-only control reservation、later-tick visibility、有界 exposure horizon、rollback 与 export-boundary finalization。存在 pending 或 overdue transaction 时，证据不完整。

当前未实现永久 retention。

### 6.7 客观评估（Objective evaluation）

evaluation 记录 post-commit Objective-Fact，不赋分。live 与 control branch 必须保留逐组件证据、branch identity、source lineage、evaluation cost 与 support。runtime 不自动执行 keep/revert。

## 7. 引导读出（Bootstrap readout）与寻址（addressing）

当前仅用于实验的 bootstrap 可以暴露少量角色中立 graph readout coordinate，并使用 normalized-dot candidate addressing，同时声明 threshold、delay window、runtime tie 时的 latest policy 以及 top-1 selection。

这些是固定工程塑形工具，不是通用 attention 架构。coordinate、score、rank、margin、winner age、reuse 或 basin occupancy 都没有固定主观含义。

runtime score comparator 是 selection semantics 的唯一权威。分析专用 tolerance 或 bin 必须明确标记为诊断，不得替代 runtime tie 语义。若 checksum-bound 证据证明诊断分类与 runtime 语义不一致，可以通过 qualification overlay 修正资格解释，但不得改写历史产物。

### 7.1 Categorical sampling trace

policy action sampling 仍由现有 action system 权威拥有。可选 trace 只能记录实际采样核的完整 mask、logits、probability、CDF、counter-based key/draw 和 selected interval；不得重新采样或修改 action。trace 不属于 Subject VM state、checkpoint、branch identity 或演化成本。其唯一用途是支持后续只读 action-boundary 审计。

### 7.2 Activation contribution trace

可选 activation contribution trace 只能消费同一次权威 activation 已产生的执行中间量，记录 node activation、edge transmission、output gate contribution、action-port 聚合和 active temporary-write/control-reservation lineage。writer 不得重新执行 graph、读取随机流或修改 node/edge/output。

trace payload、pending join 状态和 writer lifecycle 都不属于 Subject VM storage、configuration identity、checkpoint、clone 或 branch identity。event identity 可以在 intent 建立后由 observation 层补齐，但不得回写 runtime cognition。

该 trace 只是执行 contribution decomposition，不是 causal attribution、credit assignment、价值解释或 retention 依据。只有通过 action、RNG、checkpoint state 与 branch identity 中立性门后，才能用于后续只读分析。


### 7.3 ThoughtEvent T1 当前机制与通信的未来边界

T1 已增加与现有 graph-produced continuous token 同源的统一 ThoughtEvent arena。事件核心只包含 token、tick、entity/subject/event identity、expiry 和 parent DAG metadata；不包含 action、Objective-Fact、value、confidence 或 modulation 结果。现有 delayed-association trace 继续保持原合同，不被 arena 替代。

arena 默认关闭且有界。启用后属于 normalized configuration、checkpoint、clone 和 branch identity；禁用精确默认值会从 canonical payload 移除。parent 必须属于同一 subject、已经保留且早于 child tick；禁止 self-parent、same-tick parent 和 child append 时覆盖 active parent。当前 T1 runtime 不读取 arena，所有自动产生事件的 parent_count 为 0。

T2 已只读审计当前 fixed-bootstrap token：重复坐标负对照在九 seed 中稳定坍缩为 centered rank 1；rank-two 候选避免精确重复并保持 centered rank 2，但连续同主体 token 仍高度相似。

T3 已实现最小前向 recall。每个主体只读取最近一个严格早于当前 tick 的 retained ThoughtEvent；selector 确定性运行，不使用 query network、随机检索、temperature 或固定认知角色。recalled coordinate 通过最多一条 `node_recall_port`/`node_recall_gate` 进入普通 graph node，commit 时将实际 selected event 记录为 parent DAG edge。正式 control 证明 content、selector、parent linkage 和计数成本可分离，且 readout-only ingress 不改变 action/event 语义。

该机制仍受 T2 低秩边界限制，identity parent-child token 高度相似；它不证明已形成思维链、分布式认知、语义记忆或语言。未来能力不得把极短暂思维链和较长期记忆拆成两套 token；二者必须共享统一 ThoughtEvent vector、identity、lineage、comparator 与 graph ingress，只能通过生命周期、索引、容量和访问成本连续分化。

未来 communication region 只能是统一图与物理 SignalEvent channel 之间的接口区域，不拥有对象指称、词义、价值或语法。不同 seed/区域可以通过不同 signal、node、topology 或 region 分布实现相同功能；跨世界对齐必须保留符号置换和 graph permutation 的等价可能。完整尚未实现的设计边界见 `docs/THOUGHT_EVENT_LANGUAGE_COGNITION.md`。

## 8. 仅用于实验的干预

冻结协议需要因果操纵时，runtime 可以暴露明确的 experiment-only policy。当前实例包括 subject-time coordinate identity 与 cyclic donor alignment mode。

experiment-only intervention 必须：

- 默认关闭；
- 进入 normalized configuration 与 branch identity；
- 保持协议声明的 candidate opportunity 与 compute/storage budget；
- treatment 与 control 尽可能共用同一实现路径；
- 证明操纵实际发生；
- 不增加语义化价值或生产 policy。

这些 policy 是科学仪器，不会自动成为可演化机制。

## 9. 安全不变量

VM 必须通过机械约束或测试保证：

1. 不允许尚未实现的后果在同一 action phase 回馈当前动作；
2. 诊断标签不得反馈进 runtime cognition；
3. 长期 event storage 不保存完整网络执行历史；
4. token、event、eligibility 与 transaction 容量有界；
5. delayed update 只能在后续 tick 可见；
6. world provenance 不可变；
7. source、configuration、branch 与 checkpoint lineage 必须精确；
8. evidence export 前必须 rollback 或明确 finalization；
9. 不存在隐藏 scalar reward 或 coordinate valence；
10. action-residual path 不能有竞争所有者。

## 10. 发育、演化与成本边界

随机创始者不得支付成熟 graph 的全部成本。成本模型必须区分：

- 未表达结构；
- 已表达结构维护；
- node activation；
- edge use 与 bandwidth；
- 按容量和持续时间计算的 retained state；
- 配置存在时的 cross-region transport；
- delayed update；
- development、duplication、deletion 与 repair。

topology、region capacity、migration、duplication、deletion、inherited readout 与 addressing evolution 继续保持阻塞，直到单独的 `[EVOLVE-SUBJECT]` 合同规定 mutation、development、inheritance、cost、neutralization 与 source-health 要求。

## 11. 证据与资格

正式证据链为：

```text
合格的独立 source checkpoint
→ 声明的 paired 或 multi-arm branch plan
→ guarded-live 与匹配 read-only control
→ 验证 export 与 finalization
→ integrity assessment
→ source-balanced component assessment
→ frozen result ledger
```

普通独立重复单位是 source checkpoint。同一 source 内的 entity、window、event、coordinate 和 tick 是相关观测。

assessment 必须区分：

- prerequisite/support failure；
- manipulation 或 dose failure；
- identity、lineage 或 export failure；
- observation-coverage failure；
- path-dependent 或 source-sparse effect；
- source-replicated effect。

方向混合的组件不得压缩成隐藏 utility score。

## 12. 实现边界

权威实现位于 `src/se/subject_vm/`，包括：

- configuration 与 port contract；
- storage 与 lifecycle；
- activation 与 runtime orchestration；
- trace 与 delayed association；
- eligibility 与 modulation；
- transaction、guarded live write 与 update safety；
- evaluation 与 export；
- ownership 与 binding。

集成点保持精简：

- 全局配置只拥有版本化 schema；
- runtime orchestration 只调用 phase boundary；
- action policy 消费有界 potential，但不拥有 graph internals；
- checkpointing 委托 graph snapshot/restore；
- evolution 委托 lifecycle，以及获授权后的 mutation；
- reporting 只读。

不得仅因已有相关数据，就把 Subject VM 内部逻辑迁入 social、knowledge 或单体 simulation module。

## 13. 当前能力边界

已实现的底物能力：

- 惰性 graph schema 与 lifecycle；
- 有界 activation routing 与 action-potential output；
- continuous token 与 objective-event trace；
- local eligibility carrier；
- delayed candidate association；
- 有界 modulation proposal；
- shadow transaction；
- guarded temporary live write 与 rollback；
- 无 score 的 objective evaluation；
- paired/multi-arm export、integrity 与 reproducibility assessment；
- experiment-only alignment intervention；
- 语义中立 categorical sampling trace，可导出完整 mask、logits、probability、CDF 与 draw，但不进入 checkpoint 或 branch identity；
- 外部只读诊断研究。

尚未授权或尚未作为通用能力实现：

- 自动 value assignment；
- 自动 keep/revert；
- 永久 retention；
- learned attention/addressing weight；
- online topology evolution；
- 语义化 partner、trust 或 role network；
- 前向 ThoughtEvent recall、思维链与 communication-language mapping；
- Epoch 1 资格或主体性结论。

当前科学前沿和下一任务刻意不写在这里；见 `docs/PROJECT_STATUS.md` 与 `docs/SCIENTIFIC_ISSUES.md`。

## 14. 权威引用

| 需求 | 权威位置 |
|---|---|
| 项目级许可与解释边界 | `PROJECT_CHARTER.md` |
| 跨版本推断规则 | `PROJECT_GOVERNANCE.md` |
| 当前系统依赖结构 | `ARCHITECTURE.md` |
| 机器可读 VM 决策 | `protocols/decisions/subject_graph_vm_*.json` |
| 已冻结 Stage 3C 结果 | `docs/results/SUBJECT_VM_STAGE3C_RESULTS.md` |
| 当前任务前沿 | `PROJECT_STATUS.md` |
| 当前开放问题 | `SCIENTIFIC_ISSUES.md` |
| 尚未实现的 ThoughtEvent 与语言研究合同 | `THOUGHT_EVENT_LANGUAGE_COGNITION.md` |

具体研究中，若自然语言与可执行 decision protocol 冲突，以冻结协议控制执行；二者都不得超出 Charter 规定的解释边界。
