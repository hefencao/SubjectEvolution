# Partitioned Subject Graph VM v1

Status: **Stage 3C-5 CPU-reference score-free objective evaluation windows implemented; no automatic keep/revert decision**
Project version: **0.131.0**

## 1. Decision

SubjectEvolution will not continue the D1-X/Y primary path of adding one designer-defined ledger for each named benefit class. The next subject-formation substrate is a **partitioned unified subject graph**:

- one node and edge identity system;
- several initially biased computational regions that reduce evolutionary search time;
- one shared routing substrate;
- separate activation and delayed plasticity phases on the same graph;
- no built-in concepts such as benefit, trust, friend, enemy, knowledge value, loyalty or role.

The project may prescribe a general cognitive architecture because cognition architecture is not itself the research target. It must not prescribe the concrete cognition that occupies that architecture.

In short:

> The project may predefine brain-like regions and causal timing, but not what those regions must believe, value or represent.

## 2. Scope and non-goals

This design exists to make long-horizon subject formation computationally reachable. It is not intended to discover every possible cognitive architecture from an unstructured graph.

The design does not:

- define a universal reward or utility signal;
- define material gain, accurate knowledge, protection or reproduction as internally positive;
- define partner classes, social roles or group membership;
- require an Actor-Critic decomposition;
- require a permanently separate attribution, knowledge, interest or policy network;
- replace the external scientific definition of continuation benefit used by observers and counterfactual analyses.

The engine continues to define physical consequences. Evolution determines which internal structures survive those consequences.

## 3. Architecture prior versus cognitive content

### 3.1 Allowed architecture priors

The fixed runtime may provide:

- fast and slow update domains;
- bounded persistent state;
- delayed event eligibility traces;
- action-facing integration capacity;
- region-local and cross-region routing costs;
- phase-ordered activation and later plasticity;
- generic operators such as delay, decay, accumulation, gating, comparison and sparse selection;
- developmental activation and expression costs;
- immutable event provenance supplied by the world runtime.

These are search-space and implementation constraints.

### 3.2 Forbidden concrete cognition

The runtime must not encode rules such as:

- resource receipt increases partner value;
- prediction accuracy increases trust;
- injury creates hostility;
- sharing creates cooperation;
- group outsiders are conflict targets;
- energy, integrity or reproduction coordinates have fixed subjective valence;
- one region is intrinsically a friendship, language, scout, leader or obedience system.

Such meanings may be diagnosed after emergence, but cannot be initialized as answers.

## 4. One graph with initially biased regions

The subject graph is one evolvable graph whose nodes share stable identities and a common edge schema. Regions are developmental priors, not independent services or permanent semantic modules.

### 4.1 Fast sensorimotor region

Properties:

- updates every policy tick;
- reads immediate observation and body state;
- has short or absent persistence;
- has low execution cost;
- supplies the minimum role-neutral survival path;
- may write action-facing activations.

It is not predefined as foraging, fleeing or aggression cognition.

### 4.2 Persistent-state region

Properties:

- supports bounded state retention across ticks;
- supports multiple decay scales;
- stores compressed internal state and optionally content references;
- pays capacity and retention cost;
- can be read or written through the shared router.

It may later carry spatial, source, partner or self-state representations, but none is preassigned.

### 4.3 Delayed-association region

Properties:

- receives objective event deltas only after the relevant action phase;
- can access bounded graph-produced internal tokens and objective event facts;
- supports delayed, accumulated and residual updates;
- cannot alter the action whose outcome has not yet occurred;
- does not contain fixed positive or negative outcome labels.

This region creates favorable conditions for attribution-like functions without prescribing attribution answers.

### 4.4 Integrative-drive region

Properties:

- combines immediate inputs, persistent state and delayed-association state;
- can directly influence action-channel activation;
- permits recurrence and long-lived internal dynamics;
- is the main architectural location where interest-like internal organization and decision can overlap.

It is not supplied with an external reward input. Subjective attraction, avoidance and trade-offs must arise from evolved topology, parameters and state dynamics.

## 5. Region boundaries and overlap

The first implementation may use hard region membership for bounded engineering risk. The schema must nonetheless support later mutation of:

- region capacity;
- node region assignment;
- cross-region bandwidth;
- update frequency;
- retention scale;
- plasticity eligibility;
- region duplication, contraction or deactivation.

A later schema may replace hard membership with a region-membership vector. Region names remain architectural labels and cannot be used as scientific evidence of cognitive function.

## 6. Unified node and edge contracts

### 6.1 Node contract

Every expressed node has at least:

- stable node ID within a subject lineage state;
- region assignment;
- generic operator ID;
- bounded internal state;
- activation schedule;
- expression gate;
- state-retention parameters;
- plasticity gate;
- structural and execution cost metadata;
- optional generic continuous-token readout port and gate.

Node operator IDs must be cognitively neutral. The initial operator set should be small enough to audit and expressive enough to combine.

### 6.2 Edge contract

Every expressed edge has at least:

- source node or approved external port;
- target node or approved output port;
- forward activation weight or gate;
- delay;
- bandwidth;
- persistence or eligibility parameters;
- plasticity participation flag;
- phase permissions;
- structural and use cost.

Knowledge, latent state, memory and action modules must not each invent a separate incompatible edge identity.

## 7. Shared routing with two causal phases

Interest and decision may be highly overlapping because they can occupy the same graph and recurrent state. The required separation is temporal, not necessarily modular.

### 7.1 Activation routing

During the action phase:

```text
observation / body state / retained state / messages
→ subject-graph activation
→ internal state updates allowed for this phase
→ action-channel potentials
→ existing action arbitration and world execution
```

### 7.2 Delayed plasticity routing

After real consequences exist:

```text
historical graph-produced token
+ later objective state and event facts
+ short-lived local eligibility or another frozen local bridge
→ delayed association and future graph changes
```

The runtime does not require any event magnitude to be distributed. Unassociated objective facts may remain unexplained and expire with bounded token/event history.

### 7.3 Phase safety

The first implementation must mechanically enforce:

1. an action cannot receive credit from its own not-yet-realized outcome;
2. long-term history cannot retain a complete node/edge execution path;
3. any future micro-level update requires a separately bounded local eligibility bridge;
4. plasticity changes affect later ticks only;
5. world provenance cannot be rewritten by the subject graph;
6. diagnostic observers cannot feed labels back into the graph.

## 8. Event and provenance substrate

The engine records objective facts, not cognitive interpretation. A bounded event record may include:

- event ID and tick;
- stable subject IDs participating in the physical event;
- action and target identifiers;
- location and relevant physical context;
- objective pre/post state delta;
- content or signal provenance that actually entered computation;
- graph-produced bounded continuous internal token;
- parent or source event IDs where physically defined.

The engine must not preserve unlimited free history for every subject. World event retention, token/event retention, short-lived local eligibility and subject-owned memory are separate capacities.

## 9. Development, cost and evolutionary accessibility

The graph must not impose a mature cognition cost on random founders.

Required cost separation:

- unexpressed node: approximately zero runtime cost;
- expressed node: structural maintenance cost;
- activated node: execution cost;
- retained state: capacity × duration cost;
- active edge: bandwidth/use cost;
- cross-region edge: optional additional transport cost;
- plasticity update: update cost;
- structure creation or duplication: developmental cost.

Initial subjects retain a minimal sensorimotor path. Persistent, delayed and integrative capacity begins sparse or weak and can be activated incrementally by mutation and development.

Cost is necessary but not the only pruning mechanism. Bounded capacity, overwrite, decay, deletion and route competition must support lifecycle garbage collection.

## 10. Relationship to current components

| Existing component | Subject Graph VM role |
|---|---|
| action strategy | existing action arbitration/output boundary; later fed by graph action potentials |
| latent router | candidate base for generic activation routing, not a separate semantic network |
| working-memory router | candidate persistent-state substrate |
| knowledge copies and provenance | objective content/reference store available to routed computation |
| functional modules | candidate generic node/operator implementations |
| sparse selection | candidate graph and route gate primitive |
| stable subject IDs | provenance and cross-checkpoint identity boundary |
| D1-X/Y ledgers | retained fixed-cognition comparison baselines and engineering test fixtures |
| trust/group graph | legacy observational grouping only; not the emerging subject graph |
| epoch checkpoint | must eventually save topology, region state, routes and developmental expression |

No existing component is automatically accepted as the final implementation. Adapters must preserve one dependency direction and avoid parallel competing routers.

As of v0.110, this is enforced rather than left as documentation: Stage-2 Subject VM is the sole optional action-residual owner. Legacy knowledge residual, latent, working-memory and sparse-selection routes remain available only when Stage 2 is not active. Knowledge provenance, functional modules and candidate/group graphs may coexist solely as objective storage, embodied mechanisms or observations and are not imported into Subject VM.

## 11. Status of D1-X and D1-Y

D1-X and D1-Y are rejected as the primary scientific model of subject formation because they prescribe semantic benefit channels and update formulas.

They remain useful for:

- testing delayed state and checkpoint compatibility;
- testing stable source provenance;
- testing long-window reporting;
- serving as simple fixed-cognition comparison baselines;
- demonstrating what a future evolved graph must outperform.

No further primary-path expansion should add protection, conflict, opportunity-cost or other named ledgers to D1-X/Y.

## 12. Implementation sequence

### Stage 0 — contract freeze (v0.107)

Deliverables:

- this architecture document;
- machine-readable Subject Graph VM contract;
- revised Epoch 1 functional qualification contract;
- immutable decision that D1-X/Y are comparison baselines;
- project charter, governance, status and architecture alignment.

No runtime behavior changes.

### Stage 1 — inert graph schema and storage (implemented in v0.108)

Implemented:

- versioned disabled-by-default config schema;
- fixed-capacity node, edge, region and state storage;
- checkpoint, clone, birth/death and region-branch handling;
- configuration identity normalization;
- zero-output and zero-cost disabled path;
- CPU reference lifecycle tests.

Acceptance met on the CPU reference path: enabling an empty graph changes no entity, environment, information, social or action trajectory state. The enabled metadata/storage itself is the only added state.

### Stage 2 — activation routing adapter (implemented in v0.109)

Implemented:

- frozen `objective-entity-input-ports-v1` and `action-potential-output-ports-v1`;
- region update periods plus deterministic within-tick activation phases;
- four bounded role-neutral scalar operators;
- strictly earlier-phase zero-delay routing and previous-state one-tick routing;
- edge bandwidth, node activation and aggregate output bounds;
- additive integration into existing policy logits before existing feasibility masks and categorical arbitration;
- checkpointed structural/use accounting as counts only;
- no delayed plasticity, physical energy debit or random-number consumption.

Acceptance met on the CPU reference path: hand-constructed role-neutral graphs reproduce deterministic bounded transformations, Stage-2 empty graphs remain exactly neutral, and v0.108 Stage-1 checkpoints restore with inert activation bindings.

### Stage 3A — compact internal token and objective-event trace (implemented in v0.111)

Implemented:

- graph-selected generic token readout ports and gates;
- continuous fixed-width token geometry rather than cryptographic hash identity;
- bounded per-subject token/event ring and expiry;
- actual action-resolution and objective post-commit state deltas;
- no persistent executed-node IDs, transmitted-edge IDs, activation masks or full graph snapshots;
- memory independent of graph node/edge capacity;
- birth/death/compaction/checkpoint/clone lifecycle integration;
- no eligibility, credit, plasticity, fixed valence or same-tick feedback.

Acceptance met on the CPU reference path: nearby node values produce nearby token values, only graph-expressed readouts create records, Stage 3A is behavior/RNG neutral relative to Stage 2, and checkpoint/lifecycle round trips preserve bounded history.

### Stage 3B-1 — short-lived local eligibility carriers (implemented in v0.112)

Implemented:

- graph-owned per-node and per-edge participation flags and bounded gates;
- local node marks from actual executed node output;
- local edge marks from actual bandwidth-bounded transmission;
- deterministic elapsed-tick decay and fixed-horizon expiry;
- exact checkpoint, clone, compaction and death handling;
- structural inheritance with dynamic value/age reset on birth;
- no copy into the persistent token/event ring;
- no objective-event write, value assignment, parameter update or same-tick feedback.

Acceptance met on the CPU reference path: local marks depend only on graph-selected actual activity, expire without external events, survive exact replay, and leave action outputs and RNG consumption neutral relative to Stage 3A.

### Stage 3B-2 — delayed association and generic modulation (not implemented)

Future work may implement:

- later-tick association between historical continuous tokens and objective events;
- generic modulation of still-live local eligibility;
- generic delayed update operators;
- unexplained residual through unassigned events;
- later-tick-only state changes;
- no fixed valence mapping.

Acceptance will require the same objective event facts to produce different future changes under different inherited graph parameters without changing event facts or persisting a whole-network path history.

### Stage 4 — developmental variation and lifecycle pruning

Implement:

- heritable region capacities and cross-region bandwidth;
- node/edge activation, deletion, duplication and migration;
- bounded retention and overwrite;
- separate structural, runtime, memory and plasticity costs;
- mutation that can remain dormant before expression.

Acceptance: random founders do not pay mature-graph costs and small active structures can survive long enough to be selected.

### Stage 5 — emergence studies and Epoch 1 qualification

Only after substrate health:

- compare against reflex, proximity, kinship, recent-event and D1-X/Y fixed baselines;
- test delayed history influence on behavior;
- neutralize graph state, plasticity or key cross-region routes from shared checkpoints;
- test cost compensation and multi-seed/multi-generation persistence;
- accept functionally equivalent but internally different solutions.

No group-rule implementation begins before this stage passes.

## 13. Initial implementation file boundaries

Preferred new modules:

```text
src/se/subject_vm/config.py
src/se/subject_vm/storage.py
src/se/subject_vm/lifecycle.py
src/se/subject_vm/runtime.py
src/se/subject_vm/__init__.py

# Stage-2 modules implemented in v0.109:
# activation.py, ports.py
# Deferred Stage-3/4 modules:
# traces.py, plasticity.py, costs.py
```

Integration points should remain thin:

- `cfg.py`: versioned configuration only;
- runtime orchestration: phase calls only;
- action policy: receives bounded action potentials, does not own graph internals;
- checkpointing: delegates graph snapshot/restore;
- evolution lifecycle: delegates graph birth/death/mutation;
- reporting: reads diagnostics, never alters state.

Do not place the new implementation into `subjects/social.py`, `knowledge/system.py` or `runtime/sim.py` merely because related data already exists there.

## 13.1 v0.108 Stage-1 implementation status

The Stage-1 runtime uses a tiny disabled null object and allocates fixed arrays only when explicitly enabled. It binds every occupied row to a current entity ID and stable primary subject ID, inherits structure without dynamic state, clears rows before slot reuse, and delegates checkpoint/clone/regional-branch handling through the existing lifecycle.

The Stage-1 CPU/GPU-hybrid contract remains intentionally inert and host-authoritative: no device graph allocation, graph synchronization, RNG use, action output or graph cost.

A missing graph field in a compatible checkpoint is reconstructed only as an empty container. No historical expression, state, eligibility or plasticity is fabricated.

## 13.2 v0.109 Stage-2 implementation status

The Stage-2 contract is frozen in `protocols/decisions/subject_graph_vm_activation_v1.json`. It exposes 16 objective scalar inputs and eight action-potential outputs. Input names describe engine coordinates only; they do not define subjective value.

The CPU reference executor uses retained scalar state coordinate zero as the current node activation. It supports bounded linear, tanh, retained-linear and retained-tanh operators. Update periods determine whether a node runs on a tick; activation phases determine deterministic within-tick order. A zero-delay edge requires a strictly earlier source phase, while a one-tick edge reads the prior retained state. Same-phase execution is order-independent.

The runtime adapter adds bounded graph outputs to the existing policy logits before the existing physical action mask and categorical arbitration. The graph does not own action sampling, intents, conflict resolution or world settlement.

Structural and use units are counted and checkpointed, but no physical energy is deducted. This prevents a temporary engineering coefficient from becoming an implicit selection function before developmental accessibility and cost compensation are frozen.

Stage-2 execution is CPU-reference-only. GPU construction with a Stage-2 configuration fails explicitly. This is not a GPU parity claim or packed graph representation.

## 13.3 v0.110 routing ownership and legacy disposition

The repository deliberately retains pre-Subject-VM implementations because frozen configurations, checkpoints, ablations and fixed-cognition comparison panels depend on them. Retention is not co-ownership. `subject_vm/ownership.py` and `subject_graph_vm_legacy_router_disposition_v1.json` freeze the following boundary:

- inherited action strategy remains the minimal genetic/sensorimotor baseline;
- existing masks, sampling, intents and world settlement remain the physical action authority;
- Stage-2 Subject VM is the sole optional primary-path action-potential residual owner;
- knowledge residual, latent router, quantized working memory and sparse selection cannot coexecute with Stage 2;
- knowledge provenance remains an objective external store reachable only through future narrow references or ports;
- functional modules remain embodied mechanisms and are not copied into graph identity/state;
- candidate-subject and group graphs remain observations and cannot publish graph state, action bonuses or plasticity.

No automatic migration converts old semantic router genes, memory coordinates or ledgers into Subject VM nodes and edges. Such conversion would falsely present designer-built fixed cognition as an emerged unified graph. Generic arithmetic or selection primitives may be reused only after a separately versioned role-neutral extraction.

## 14. Deferred decisions

The following remain intentionally open after the Stage-2 CPU reference prototype:

- hard versus continuous region membership after v1;
- whether edge plasticity changes weights, gates, state or all three;
- how much topology changes during life versus reproduction;
- CPU/GPU packed representation;
- quantized deterministic update semantics;
- historical subject-memory persistence after death;
- externalized/shared graph state for Epoch 2.

These are implementation choices, not permissions to add concrete cognitive semantics.

### Stage 3B-2 — bounded delayed association candidates (implemented in v0.113)

Stage 3B-2 introduces a bounded content-addressing step but still does not perform credit or plasticity.

One continuous token coordinate is configured as a role-neutral request gate. A positive request above threshold asks the existing per-subject event ring for one older token candidate. The request coordinate is removed before normalized-dot similarity so the control signal cannot improve its own match. Only events inside a strictly positive configured delay window are eligible, and that window cannot exceed either event retention or local eligibility lifetime.

The result may be unassigned. When assigned, the current event stores only the historical event ID, historical tick, delay and similarity. This is a candidate link between a later objective event record and an earlier graph-produced representation. It does not assert causality, value, correctness or semantic identity.

No event fact changes local eligibility in this stage. No graph parameter is updated, no topology is modified, no physical cost is debited and no random value is drawn. Stage 3B-2 therefore remains behavior-neutral relative to Stage 3B-1 for the same graph and simulation seed.

A later stage may propose modulation only from a committed delayed candidate and still-live local eligibility. That later contract must preserve no-update outcomes, prevent current-tick self-confirmation and keep designer event semantics out of the update path.


## v0.114：Stage 3B-3 调制提案不是参数更新

Stage 3B-3 只在已经分配的延迟候选上生成一个可拒绝、定长的参数族提案。统一图通过连续 token 提供提案请求、客观事实投影权重和六个通用参数族方向。运行时只计算当前事件与候选历史事件的客观事实差，并用图产生的权重形成有界向量。

提案控制坐标全部从关联相似度中移除；关联相似度和延迟也不参与提案强度。因此“相似”仍只是内容地址，不是因果信用。能量、完整性、资源、信息、繁殖或行动成功等坐标没有引擎规定的正负价值，只有图产生的投影符号能够选择或反转它们。

提案只到参数族，不绑定具体节点或边，不读取或复制 eligibility 快照，不写 node bias、gate、edge bandwidth、retained state 或 topology。原因是当前 tick 的局部 eligibility 可能与较早活动聚合在同一载体中；在没有冻结历史/当前活动隔离、回滚、累计稳定性和物理成本前，直接写入会重新引入同 tick 自我确证和隐藏选择函数。

当前证据只支持：已提交的历史候选和客观事实差能够被图控制的连续投影转换为可审计、可拒绝、行为中性的参数族提案。它不支持已经完成归因、学习、价值形成、参数塑性或主体性。


## v0.115：Stage 3C-1 使用 bootstrap 注意偏置完成精确目标提案

本项目允许为了缩短从混沌状态塑形的时间而预设可替换的通用认知偏置。现有 normalized-dot 单历史候选寻址和单赢家局部资格选择因此继续作为 bootstrap baseline，而不是立即切换到难以验证的完整通用注意模型。

Stage 3C-1 在当前 tick 新活动发生前，从衰减后的局部 eligibility 中为六个参数族各选最多一个候选。当前行动新产生的资格不会进入该候选快照。世界提交后，参数族提案只能绑定该有界快照；没有候选时保持未绑定。该阶段仍不生成最终参数 delta，不修改节点、边或拓扑。

## v0.116：Stage 3C-2 只形成带事务守卫的候选 delta

Stage 3C-2 保留 v0.115 的 bootstrap 内容寻址和单赢家资格绑定。它不切换到完整通用注意模型，而是先修正永久写入前最明显的工程风险。

每个 bound target 会在事件提交时重新验证 stable ID、slot、expressed 状态、参数族和必要端口。通过验证后，参数族提案、激活前历史 eligibility 与配置步长形成候选 delta。候选依次经过每族 clip、每事件 L1 比例缩放和参数上下界投影。当前参数值作为未来 compare-and-swap 与 rollback 守卫保存。

该阶段没有 apply 接口，参数数组、eligibility、retained state 和 topology 均不改变。未执行提案也不占用实际长期更新预算。下一阶段必须先建立原子 dry-run/transaction 合同，再决定是否允许任何永久参数变化。


## v0.117：Stage 3C-3 只在影子事务中验证 CAS 与回滚

Stage 3C-3 不把 v0.116 的候选 delta 写入统一主体图。每个事件的全部候选首先重新核验 stable target identity，并对 live float32 参数执行位级 compare-and-swap。任意目标失败会中止整个事件，禁止部分影子提交。

通过检查的 projected value 只写入固定六维私有影子向量，随后恢复为 captured pre-state 并验证回滚位级一致。影子向量不会进入节点/边存储，也不影响行动或后续 eligibility。事务保存 request、prepare、CAS、shadow apply、rollback 和 count-only cost 证据；`permanent_write_authorized` 始终为 false。

这仍只是 bootstrap 学习链的工程安全验证，不证明历史关联、目标绑定或 delta 方向具有真实因果正确性。


## v0.118：Stage 3C-4 只允许显式 opt-in 的短窗口 live write

Stage 3C-4 不把影子事务直接升级为永久塑性。只有 `live_write.enabled=true`、Stage 3C-3 已 prepared 且 rollback-verified、第二次 float32 CAS 仍匹配、同一稳定目标没有 pending 写入并且窗口预算未耗尽时，事件事务才可 all-or-none 写入 live graph。

写入进入固定容量 applied ledger，记录事件、稳定目标、pre/post 值、apply tick 与 rollback due tick。到期时 runtime 在激活前对 post 值执行精确 CAS，并 all-or-none 恢复 pre 值。任何回滚异常会锁定该主体未来写入。`enabled=false` 提供相同 Stage 3C-4 合同下的 trajectory-neutral control。

该阶段不定义 objective event 的正负价值，不判断更新是否有益，不扣实体能量，也不授权 topology、retained state 或跨代永久参数变化。


## v0.119：Stage 3C-5 只记录无分数的客观评估窗口

Stage 3C-5 不在主体内部判断短窗口更新是否“更好”。同一准备完成的事务在 `live_write.enabled=true` 时进入 guarded-live 臂，在 `enabled=false` 时进入 read-only control 臂。两臂使用完全相同的固定容量 ledger 和 21 维客观事实合同；实时臂只有在 Stage 3C-4 精确回滚后才能完成，控制臂在相同 horizon 完成且从不修改参数。

每个窗口只保存逐维事实累计、绝对累计、最大绝对值、观察数量、行动成功/失败数量、裁剪计数、稳定目标和 rollback integrity。它不保存完整激活路径，不生成 scalar score、reward、utility、valence、keep/revert 决策，也不在 runtime 内自动合成反事实。

真实因果比较仍需以后从同一 checkpoint 建立显式 paired branch，并携带分支身份、成本和环境扰动合同。当前证据只说明两个臂可以用同一结构收集有界证据；不能说明候选更新有效、有益或应永久保留。


## v0.120：Stage 3C-6 只在外部共享 checkpoint 合同中配对窗口

Stage 3C-6 不把 paired comparison 塞回主体运行时。`subject_vm/evaluation_export.py` 只负责把已经完成的 Stage 3C-5 窗口转换为稳定记录和模式无关的 pair key；`analysis/subject_vm_paired_evaluation.py` 负责可信 checkpoint、分支身份、运行与导出。

源 checkpoint 必须处于静止边界：没有 active evaluation window、pending live write、locked row，也不允许携带旧 evaluation/live-write 条目。计划记录 checkpoint 文件哈希、状态哈希、配置哈希、源 tick 和共同 final tick。guarded-live 与 read-only-control 两支只允许 `subject_vm.live_write.enabled` 不同，branch ID 同时绑定 source state、role、branch config 和 final tick，并写入最终 checkpoint lineage。

导出器只接受与计划匹配的两个最终 checkpoint。guarded-live 窗口必须是 verified rollback 后的完成状态，control 窗口必须是只读完成状态。配对依据稳定 subject、source event、窗口时间、目标族、稳定 target、pre/projected value 和 bounded delta；未配对窗口不会丢弃。输出可以包含逐坐标 live-minus-control 差异，但不产生 scalar score、固定坐标权重、keep/revert 指令、永久写入授权或自动因果结论。

该合同的作用是让后续工程审计能够区分“窗口数据存在”与“有效 paired evidence 存在”。它仍不证明 bootstrap 关联、目标绑定或参数方向具有因果正确性。


## v0.121：Stage 3C-7 只评估 paired evidence 的充分性与完整性

Stage 3C-7 不进入主体图激活、资格、写入或回滚路径。`analysis/subject_vm_paired_evidence.py` 读取一个或多个 Stage-3C-6 导出，并重新验证导出 checksum、分支 checkpoint 文件哈希和状态哈希。重复使用同一个 source state 的导出会被显式计数，不能伪装成独立重复。

评估报告保留 paired、unpaired live 和 unpaired control 的数量与覆盖率，并按稳定主体缺失、source event 分化、窗口边界分化、target/update 合同分化等结构原因分类。它同时读取最终 ledger，报告 rollback failure、pending write、locked row、事实裁剪和同窗 evaluation count-cost 是否匹配。分支分化只按实体身份、主体身份、实体状态和环境字段逐分量报告，不被自动解释为失败或收益。

默认的三个独立 source pair、最低覆盖率、最大裁剪率等仅是可覆盖的工程筛查参数。筛查通过不等于科学充分性，不授权 objective coordinate 权重、scalar score、因果效应、keep/revert 或永久参数保留。下一阶段若继续，应先检查已通过完整性筛查的多个独立 pair 上逐坐标方向和离散程度是否可复现，而不是直接压缩为单一目标。


## v0.122：Stage 3C-8 以 source checkpoint 为重复单位逐分量描述可重复性

Stage 3C-8 继续位于 `se.analysis`，不进入激活、资格、写入、回滚或 checkpoint 生命周期。`subject_vm_component_reproducibility.py` 只接受 checksum 有效且通过 Stage 3C-7 工程筛查的 assessment，并重新验证其引用的 Stage 3C-6 paired export。

分析层级固定为：独立 source checkpoint → stable subject → paired window。窗口先在主体内平均，主体再在 source 内等权平均，最后才跨 source 计算逐坐标统计。这样一个产生大量窗口的主体不能支配 source replicate，同一 source checkpoint 的重复输入也不能伪装成独立重复。

输出逐坐标保留 source replicate values、符号计数、mean、median、sample standard deviation、MAD、极值和 central quantile interval。sign-and-interval screen 只是可配置的工程描述，不表示坐标具有正向价值、更新具有真实因果性或参数应永久保留。报告没有 coordinate weighting、universal scalar objective、automatic keep/revert 或 scientific reproducibility authorization。


## v0.123：Stage 3C-9 短程成对数据研究

Stage 3C-9 不把固定 bootstrap 图描述成演化结果。它只用于让现有 token、局部资格、延迟关联、调制提案、短窗写入和回滚链在极短 CPU 运行中产生可检查数据。bootstrap profile、选中 stable subject ID 和安装 tick 都写入 checkpoint lineage。

read-only control 现在会建立虚拟 reservation，占用与 guarded-live 相同的 pending target、ledger slot、窗口目标数和绝对 delta 预算，但不会修改参数，也不会产生 live-write 成本。该修复避免 control 因缺少占位而产生大量额外窗口。

成对运行停止后可以执行 export-boundary transient finalization：不新增 tick，只通过现有 CAS 回滚所有仍 pending 的临时写入并释放 control reservation。尚未完成观察窗口不会进入证据。默认三 seed 短程 pilot 得到 38 个完整配对窗口、覆盖率 1.0、rollback failure 0、fact clipping 0 和 evaluation cost match 1.0。Stage 3C-8 中没有任何坐标通过描述性符号与区间稳定筛查；少量非零差异只出现在 3 个 source 中的 1 个，其余多为零。这些只证明工程链路可产生完整数据，并表明当前短窗 bootstrap 尚未提供稳定效果方向。


## v0.124：Stage 3C-10 漏斗、更新可见性与分支分化诊断

本阶段不改变 v0.123 的 seed、source tick、branch horizon、bootstrap subject 数、短期写入幅度、回滚期限或固定图。运行时只补两个有界原始事实：每个 token-ring 槽一个 `uint8 association_reason`，以及每个槽六个 `uint16 binding_eligibility_age`。新增内存为 `13 * entity_capacity * trace_capacity_per_subject` 字节；32 个实体、每主体 16 槽时为 6,656 字节。字段可禁用，旧 v0.123 checkpoint 缺失字段时按零恢复，不改变 disabled 配置 identity。

聚合全部留在 `se.analysis.subject_vm_stage3c10_diagnostics`：按 source 和 stable subject 报告 token→association→proposal→binding→safe update→shadow transaction→live/control admission→completed window 漏斗，保留原始拒绝原因并映射到无激活、无 token、无历史候选、相似度不足、无参数族提案、无 eligibility target、delta 过小、边界/预算拒绝、target pending、窗口预算耗尽和回滚/清算问题。它同时报告 raw/bounded/projected delta、相对参数范围比例、临时生效 tick、参数族/目标类型/区域分布、eligibility value/age、delay/similarity、历史事件和 target 重复使用、首次分支差异、准入与计数成本对称、精确参数恢复及回滚后的非参数路径依赖。

同一三 source 重跑显示：数据链并未停在激活或 token 层；64/64 已分配关联全部为 delay 1、similarity 1.0；121 个安全提案和 45 个实际临时写入全部落在 `node_bias`；每次写入只覆盖一个后续语义激活 tick。三个 source 都出现 action potential 和 sampled probability 差异，但只有一个 source 的两个主体事件改变离散 action，客观事实差异也只在该 source 出现。所有 source 的控制准入、窗口数量、计数成本、回滚和 export-boundary 清算保持对称，参数精确恢复。

因此当前证据支持“短期参数效应在离散采样之前大量消失或未跨过动作边界”，不支持更新有效/无效、稳定学习、因果信用、注意最优性或主体性。fixed nearest-token addressing 和 single-winner binding 继续作为可替换的 `fixed-cognition engineering shaping aid`；v0.124 没有调整机制变量，也没有授权永久保留。


## v0.125：Stage 3C-11 独立 source 样本充分性审计

本阶段不改变主体图激活、fixed bootstrap、候选寻址、eligibility、参数 proposal、target binding、bounded update、shadow transaction、guarded live write、evaluation window、control reservation 或 export-boundary finalization。唯一实验变化是把预声明的独立 source checkpoint 从 seeds `12301..12303` 扩展为 `12301..12309`；32 个初始实体、16 个 bootstrap subject、source tick 2、branch horizon 5、CPU backend 和 permanent retention disabled 保持不变。

`se.analysis.subject_vm_stage3c11_sample_adequacy` 验证 study、Stage 3C-8 和 Stage 3C-10 checksum，并以 source state 为最高重复单位。它报告从 3 到 9 source 的 prefix sensitivity、离散 action 分化 source 比例、trace-level objective-event 分化比例、完成窗口非零 source 比例和描述性 Wilson 区间。窗口、主体和实体都不被提升为独立 replicate；Stage 3C-8 仍按 window → stable subject → independent source 聚合。

报告区分两类 identity：单次运行的 artifact checksum 继续绑定实际 checkpoint、plan 和 export 文件；另一个 semantic-result hash 使用 source checkpoint state hash、固定参数、逐分量统计和科学边界，并排除路径、checkpoint `created_utc` 与 ZIP 容器字节元数据。这样不会削弱单次证据完整性，同时允许跨重复运行判断语义结果是否一致。

九 source study 得到 111 个完整配对窗口，pairing coverage 1.0、rollback failure 0、objective fact clipping 0、evaluation cost match 1.0。离散 action 与 trace 客观事件分化出现在 2/9 source，完成窗口客观向量非零仅出现在 1/9 source，稳定客观坐标仍为 0/21。该结果说明三 source pilot 只能作为工程样本，并显示当前五 tick fixed-bootstrap 效应稀疏；它不证明九 source 已具科学充分性，也不决定 32 实体或五 tick 是否代表更广分布。

Stage 3C-10 同步收紧诊断合同。paired admission/evaluation symmetry 只要求 live admission 与 control reservation、窗口容量和评价 counted cost 对称；live 干预已改变未来内部路径后，后续 shadow-transaction preparation 次数不必继续相等。分化时间线还必须声明有界 trace 的 tick coverage，覆盖不完整时只报告观测下界，不能把 ring overwrite 解释成完整零差异。

本阶段没有新增运行时字段、checkpoint schema、随机数消耗、第二套 branch/checkpoint/ledger owner 或长期路径记录。fixed nearest-token addressing、single-winner eligibility target 和 bootstrap graph 继续标记为 `bootstrap shaping bias`、`fixed-cognition engineering baseline`、`evolved_topology=false`、`universal_attention_claim=false`。永久参数保留、scalar reward、自动 keep/revert、因果信用正确性、稳定学习、主体性和 Epoch 1 仍未授权。


## v0.126：Stage 3C-12 trace-safe branch horizon 充分性审计

本阶段使用同一九 source panel 对比 branch horizon 5 与 8。除 horizon 外，32 个实体、16 个 fixed-bootstrap subject、source tick 2、CPU backend、association、eligibility、proposal、target binding、update safety、shadow transaction、rollback、evaluation 和 export contracts 全部不变。source checkpoint state hash 与 bootstrap lineage 必须逐 seed 相同。

Stage 3C-12 在两个 arm 的 guarded-live/control final checkpoint 中，以 stable subject 和 event tick 为键，比较五 tick 停止边界之前全部 event-shaped trace 数组。九个 source 的两个 branch prefix 均完全一致；两 arm 的 bounded trace coverage 均完整。该检查防止把不同起点、不同随机路径或 trace overwrite 误写成 horizon 效应。

五 tick arm 产生 111 个完整 paired windows，八 tick arm 产生 143 个；live commits 为 141 对 144。两 arm 都只有 3 个 discrete-action difference events，分布在相同 2/9 source；稳定客观坐标均为 0/21。八 tick 尾部没有新的 action crossing，只保留一个先前已分化 action 造成的后续 objective path difference。

因此当前证据缩小了“仅因停止过早而完全看不到离散差异”的解释空间，但不证明五 tick 普遍充分，也不证明更新有效或无效。branch horizon 与 temporary parameter exposure duration 是不同变量。下一阶段若继续，应保持 trace-safe horizon 和九 source panel，单独比较 exposure duration；不得同步改变 delta、实体数、bootstrap topology 或永久保留政策。

## v0.127：Stage 3C-13 临时参数暴露充分性审计

Stage 3C-13 保持九个 source checkpoint、每 source 32 个实体、16 个 bootstrap subject、source tick 2、branch horizon 8、CPU、bounded delta 和固定 bootstrap topology 不变，只比较 `rollback_after_ticks=2` 与 `3`。Stage 3C-5 要求 read-only control reservation horizon 与 live rollback horizon 相等，因此 `control_horizon_ticks` 同步变化；两个字段共同表示一个 exposure-duration 实验变量。

为了不让 source 配置身份变化混入比较，source checkpoint 仍从同一原始配置生成。paired plan 只允许 checksum-bound 的两个同步 exposure 字段，并在加载 source checkpoint 后同时应用到 live/control branch。九个 source 的 source state/config hash 与 bootstrap lineage 必须逐 seed 相同；每个 arm 内 live/control 的唯一分支差异仍是 `subject_vm.live_write.enabled`。跨 arm 的 read-only control thought token、action potential、sampled probability、action、resolution 和 objective-event trace 也必须逐事件相等。

实际结果中，平均每次 commit 的有效 semantic tick 从 1.000 增至 1.993，action-potential difference events 从 371 增至 423，sampled-probability differences 从 377 增至 426。这确认临时参数确实作用更久。离散 action difference events 没有增加，而是从 3 次、2/9 source 变为 2 次、1/9 source；两个 arm 均只有 1/9 source 的 completed-window objective vector 非零，Stage 3C-8 均为 0/21 稳定坐标。

extended arm 少两个 completed windows，来自 branch 结束时仍 pending 的 transaction/window。export-boundary finalization 精确恢复或释放状态，不执行新 semantic tick；这些 incomplete windows 被显式记录但不进入配对证据。该现象不是 rollback failure，也不改变 pairing coverage。

Stage 3C-13 只允许得出“连续影响更久不保证更多离散采样跨界”。它不允许把 exposure=2 或 3 写成普遍最优值，不允许把离散计数下降解释为负价值，也不授权 permanent retention、automatic keep/revert、scalar objective、causal credit、stable learning、主体性或通用注意力声明。



## v0.128：Stage 3C-14 fixed-bootstrap 参数族可达性审计

Stage 3C-14 保持九个独立 pre-bootstrap source、每 source 32 个实体、16 个 bootstrap subject、source tick 2、branch horizon 8、`rollback_after_ticks=3`、CPU、bounded delta、自动回滚和 Stage 3C-8 聚合不变。唯一正式实验变化是把固定 bootstrap 的 one-hot target-family token 从 port 23 的 `node_bias` 路由替换为 port 25 的 `node_output_gate`。两个端口都属于 modulation control coordinates，均不进入 nearest-token similarity。

每个 arm 在安装 bootstrap 前保存 quiescent source identity。assessment 要求逐 seed 的 pre-bootstrap state/config hash、primed tick 和 stable subject selection 相同；两个 profile 只能在 target-family 标签和对应 trace port 上不同。跨 arm 的 read-only control action potential、sampled probability、action、resolution 和 objective facts 必须逐事件一致；thought token 只允许同一 target weight 从 port 23 搬到 port 25。

九 source 正式结果中，两 arm 都产生 722 个 family proposal、144 个临时 commit 和 141 个完整 paired window，pairing coverage 为 1.0，rollback failure 与 fact clipping 均为 0，evaluation cost 匹配。`node_bias` arm 产生 423 个 action-potential difference 和 426 个 probability difference；`node_output_gate` arm 分别为 287 和 291。离散 action difference 为 2 对 1，但两个 arm 都只在 1/9 source 出现离散和客观事件分化，Stage 3C-8 均为 0/21 稳定坐标。

预探针中的 `node_input_gate` 不作为正式 arm：目标节点读取恒为 1 的 input port 0，因此 bias delta 与 input-gate delta 在该节点上代数等价。该事实只说明此 bootstrap 对照不可辨识，不说明两个参数族在一般图中等价。

Stage 3C-14 允许得出“参数角色影响短期连续可见性”，但不允许把更多或更少差异解释为价值、优劣或因果正确性，也不授权 permanent retention、automatic keep/revert、scalar objective、稳定学习、主体性、拓扑演化或通用注意力声明。

## v0.129：Stage 3C-15 fixed-bootstrap 局部灵敏度与退化诊断

Stage 3C-15 保持九个独立 source、每 source 32 个实体、16 个 bootstrap subject、source tick 2、branch horizon 8、`rollback_after_ticks=3`、CPU、bounded delta、自动回滚、nearest-token association 和 Stage 3C-8 聚合不变。它不新增 live-write arm，而是在外部 analysis 层从同一 quiescent source checkpoint 创建一次性 one-step probe branch。

每次 probe 只改一个固定参数槽位 `±0.05`，并使用已有 trace 读取 action potential、thought token、sampled probability、action 与客观事件。probe 结果不会写回 source checkpoint，不增加 runtime/checkpoint 字段，也不进入永久参数保留。`edge_bandwidth` 因 bootstrap 值位于上界而只做 inward one-sided probe。

诊断固定两个上下文：

```text
first-post-bootstrap
warmed-delayed-edge
```

前者检验即时节点、输出和 token 作用；后者先运行一次无干预激活，使 delay=1 的 edge 获得历史 node state。九 source 结果显示：

- `node_bias` 与 `node_input_gate` 在 float32 误差 `5.96e-8` 内退化等价，因为 node 0 读取 constant-one；
- `node_output_gate` 在两个上下文都影响 action potential；
- `node_trace_gate` 在 one-step horizon 只影响内部 token，不直接改变 action potential；
- `edge_forward_gate` 在首个上下文为零，但在 warmed context 明确影响 action potential；
- `edge_bandwidth` 在两个上下文都为零，因为 raw contribution 尚未触发 clamp，warm context 最小 margin 为 0.875。

Stage 3C-15 同时审计 eligibility reachability。node 0 的 bias/input/output family 具有 local eligibility carrier；node 7 的 trace gate 与 edge 0 的 forward/bandwidth family 当前没有 carrier。由此必须分别报告：

```text
mechanically sensitive
eligibility reachable
```

二者都不是价值或学习结论。后续若比较 eligibility shaping，只允许一次开放一个敏感但不可达的 carrier，并保持 source panel、horizon、exposure、delta、association、topology size、rollback 和 score-free evidence 不变。

## v0.130：Stage 3C-16 edge eligibility carrier 可达性审计

Stage 3C-16 固定九个独立 source、每 source 32 个实体、16 个 bootstrap subject、source tick 2、branch horizon 8、`rollback_after_ticks=3`、CPU、bounded delta、nearest-token association、single-winner binding、自动回滚与 Stage 3C-8 聚合。两个 arm 都把 one-hot target weight 路由到 token port 27，即 `edge_forward_gate`。唯一变量是 edge 0 是否启用已有的 `LOCAL_ELIGIBILITY_FLAG` 和 eligibility gate 1.0。

carrier-off arm 仍完整产生 token、association candidate 和 modulation proposal，但没有任何有效 edge carrier，因此产生 0 target binding、0 safe update、0 commit、0 completed window。它是“不可达漏斗基线”，不能作为 Stage 3C-8 的有效 paired replicate，也不能被过滤后假装成普通零效应窗口。

carrier-on arm 在相同 source panel 上产生 688 次 target binding、646 次 safe update、144 次临时 commit 和 129 个完整 paired windows。Stage 3C-7 的 pairing coverage 为 1.0，rollback failure、objective clipping 均为 0，evaluation cost 完全匹配；离散 action 与客观事件分化出现在 3/9 source，Stage 3C-8 仍为 0/21 稳定客观坐标。

两个 arm 的 pre-bootstrap state/config hash、stable subject selection、read-only control 行为以及 read-only token/association/modulation 漏斗完全一致。由此只允许得出：当前 exact-target binding 需要合法 local carrier，且 `edge_forward_gate` 在 carrier 开启后能够进入现有 guarded-live write 链。不能据此判断 carrier 正确、更新有益、形成学习、应永久保留参数或当前 fixed selector 是唯一理论结构。


## v0.131：Stage 3C-17 equal-similarity temporal tie-break 审计

Stage 3C-17 固定九 source、32 实体、16 bootstrap subject、source tick 2、branch horizon 8、exposure 3、CPU、`edge_forward_gate` carrier-on、bounded delta、自动回滚和 Stage 3C-8 聚合。唯一变量是 normalized-dot score 精确并列时选择 latest 或 oldest eligible historical token。

该变量通过 paired-plan runtime override 实施，不进入 config identity 或 checkpoint schema。两个 arm 的 source checkpoint state、pre-bootstrap config、stable subject selection 与 read-only objective behavior 完全一致。

latest arm 的 1008 次 association 全为 delay 1；oldest arm 的 delay 为 1–6，但每 source 只使用 32 个历史事件并最大复用 6 次。两者均为 similarity 1.0，说明差异来自 tie-break 而不是 score。latest/oldest 分别产生 129/105 个完整窗口和 3/9、2/9 source 客观分化，Stage 3C-8 均为 0/21。不得把此结果解释为 recency 价值、credit 正确或学习。

## v0.132：Stage 3C-18 有界候选分配审计

Stage 3C-18 固定九个独立 source、每 source 32 个实体、16 个 bootstrap subject、source tick 2、branch horizon 8、exposure 3、CPU、`edge_forward_gate` carrier-on、latest-on-tie、bounded delta、自动回滚和 Stage 3C-8 聚合。唯一变量是每个当前事件最多选择一个还是两个历史候选。

Top-2 仍使用相同 normalized-dot score、候选集合、threshold 和 delay bounds。两个候选的 21 维客观事实向量做等权均值，然后只形成一个 modulation proposal，并继续使用原有单事件 delta/update budget。等权不是学习出的 attention weight，也不具有价值或因果语义。

正式九 source 结果中，top-1 与 top-2 都有 1008 个 assigned current events。Top-2 新增 864 个 delay=2 secondary references，使 modulation proposal 从 942 增至 970、完整窗口从 129 增至 137，但 commit 均为 144。每 source 唯一历史事件仍为 112；top-2 只是让其中 96 个事件各被引用两次。离散 action 差异从 4 降至 2，客观分化 source 从 3/9 变为 2/9，两个 arm 均为 0/21 稳定客观坐标。

这说明 candidate cardinality 会实质改变连续漏斗和证据窗口，但当前 top-2 没有增加历史事件覆盖、写入次数或跨 source 稳定方向。不得据此给候选数、delay 或等权聚合赋予好坏含义，也不得继续无分析地增加候选数或引入 learned weights。

Trace schema 升级到 v9，仅在 association 启用时增加五个固定容量审计数组；内存增长为 `25 × entity_capacity × trace_capacity_per_subject` bytes。旧 checkpoint 的已有 primary association 恢复为 selected count 1，secondary 字段为空。默认 candidate limit 仍为 1，旧配置 identity 不变。


## v0.133：Stage 3C-19 token geometry 可分辨性诊断

Stage 3C-19 不修改运行时。它在冻结九 source 的 read-only-control trace 上，先排除 association request 与 modulation control ports，再分析 normalized-dot 实际可见的 token 子空间。当前 32 维 token 中只有 ports 29、30、31 可见，全部 1152 个 token 都等于 `[0,0,1]`。每 source centered covariance rank/effective rank 为 0，uncentered direction rank 为 1。

全部 3888 个 delay-eligible query/candidate pair 都是精确相同向量，score 全为 1.0，best-second spread 全为 0，threshold margin 固定为 0.2。因此当前 score 没有内容区分能力，Stage 3C-17/18 的排序只能由时间 tie-break 和 candidate limit 决定。该结论只适用于当前 fixed bootstrap readout 与 operating point，不证明一般 token、学习或主体机制不可能。

## v0.134：Stage 3C-20 association-visible graph-state readout 可达性审计

Stage 3C-20 保持九 source、32 实体、16 bootstrap subject、source tick 2、branch horizon 8、exposure 3、CPU、`edge_forward_gate` carrier-on、latest、top-1、bounded delta、自动回滚和无永久保留不变。唯一变量是 action-producing node 0 是否额外把当前标量状态通过 trace gate 1.0 写入 association-visible token port 29。

该 readout 不改变 node 0 的执行、action-potential 输出、参数、eligibility、similarity、threshold、delay bounds 或 candidate allocator。它只作为 explicit fixed-bootstrap readout shaping bias 写入 bootstrap profile/lineage，不进入项目 config identity，也不增加 checkpoint schema 或持久数组。

九 source 中，baseline 的 visible centered rank 为 0；readout arm 每 source 有 7 个精确 token、centered rank 为 1，normalized-dot score 不再全部为 1.0，best-second spread 为正。但每个 tick 内 16 个 subject 的 port-29 值完全相同，九个 source 也共享同一时间轨迹。因此当前 readout 只提供 global temporal phase，不提供 subject/event-specific identity。

readout arm 的 selected association 从 1008 个 delay-1 变为 864 个 delay-2，proposal、窗口与离散分化没有增加；两个 arm 均为 0/21 稳定客观坐标。不得把 score spread 解释为因果质量、价值或学习，也不得据此授权 permanent retention、learned weight、扩大 top-k 或切换完整通用注意架构。

## v0.135：Stage 3C-21 主体/事件特异 Objective-Input Readout 审计

Stage 3C-21 在两个 arm 中都使用同一 readout-only node 8：无 action output、无 local eligibility、trace port 29、trace gate 1.0。唯一变量是 objective input port 0（constant-one）或 port 11（uncertainty-mean）。九 source 的 pre-bootstrap state/config、主体选择和 read-only objective behavior 完全一致，token 差异仅限 port 29。

Port 11 arm 在每个 source 的每个 retained tick 都产生主体间方差，143/144 个主体具有时间变化，且不同 source 的 subject/event matrix 不同。normalized-dot score 不再完全并列，selected delay 分布扩展到 1–6。但 unique associated event coverage 降至每 source 85–94、最大复用升至 3，说明“可分辨”不等于“历史证据更丰富”。两个 arm 的 commit 都为 144，稳定坐标都为 0/21。

该 readout 仍是 fixed-cognition engineering shaping aid；uncertainty 的符号和大小没有固定价值语义。结果不授权永久写入、自动 keep/revert、学习、主体性或通用注意力声明。

## v0.136：Stage 3C-22 历史事件选择覆盖与复用集中度审计

Stage 3C-22 不修改运行时、checkpoint schema、相似度、threshold、候选数、tie-break、更新幅度、exposure、rollback 或永久保留。分析器从 Stage 3C-21 两个 arm 的 read-only control checkpoint 中重建每个 query 的完整同主体历史候选集合，并按现有 request/modulation control-port 排除规则、delay bounds、normalized-dot threshold、latest 和 top-1 精确复算选择。存储结果与复算选择必须逐事件一致。

九个 source 中，constant 与 uncertainty arm 的候选机会完全相同：每 source 112 个唯一 delay-valid/nonzero/above-threshold 历史事件、432 个 above-threshold query/candidate references，以及 112 个实际 assignment。差异只发生在排序与最终 identity 分配。

constant latest-on-tie 基线使 112 个历史事件各被选择一次。uncertainty readout 只选择 85–94 个事件，18–27 个仍符合 threshold 的事件未被选择，最大复用升至 3。每 source 的 identity coverage 为约 0.759–0.839，inverse-Simpson effective coverage 为约 0.644–0.747，且 uncertainty 所选 identity 在全部 source 中都是 constant 所选集合的严格子集。

该结果只证明 subject/event-specific score geometry 会改变排序并提高复用集中度，不证明更多 identity coverage 更好、重复使用更坏、credit 正确、学习形成或应该永久写入。constant 的 100% identity coverage 也是 latest 单步选择的固定工程偏置，不是理论最优。下一边界只能先做第二个无价值语义 visible coordinate 的只读筛查，并要求 rank-two、主体/事件特异 geometry；不得同时修改 addressing、top-k、delta、retention 或完整注意架构。

## v0.137：Stage 3C-23 双 Readout Rank-2 可达性审计

Stage 3C-23 在 experiment-only fixed bootstrap 中增加一个可选 readout-only node 9。node 8 固定把 uncertainty-mean 写入 token port 29；node 9 写入 port 30，且无 action output、无 local eligibility。正式对照只把 node 9 input 从 port 11 的重复 uncertainty 坐标切换为数据筛选出的 port 7。旧配置、默认 bootstrap、checkpoint schema 和永久保留状态不变。

候选筛选要求九个 source 全部达到 centered rank≥2、每 tick 有主体间方差、每主体有时间方差，并且不让任何 query 丢失全部 threshold 以上历史候选。port 7 按跨 source 最小残差方差最大规则被选择；该规则不解释其符号或大小的价值。

正式结果在 9/9 source 中达到 rank 2，但 commits 仍为 144，稳定客观坐标仍为 0/21。该结果只说明第二个主体/事件特异可见坐标机械可达，不授权 learned attention、因果 credit、永久写入或主体性结论。

## v0.138：Stage 3C-24 Rank-2 选择覆盖与 Score Margin 审计

Stage 3C-24 不修改 VM。它复用 Stage 3C-23 的十节点 rank-one/rank-two readout arms，从 read-only control trace 中逐 query 重建 delay-valid、nonzero、above-threshold 候选，并使用正式 normalized-dot、threshold 0.8、latest/top-1 排序精确复算 winner。

两个 arm 每 source 都有 112 个唯一 eligible 历史事件和 432 个 eligible references。Rank-one 仍有大量 exact best-score ties；rank-two 在九个 source 中全部消除 exact ties，但 selected identity coverage 从 0.759–0.839 下降到 0.714–0.786，maximum reuse 从 3 提高到 4，effective identity coverage 下降。Rank-two 没有选择任何 rank-one 未覆盖的新 identity。

该结果说明第二坐标改变了 score ordering 与 winner determinacy，但没有扩大证据身份覆盖。不得把更高 rank、更大 margin 或更确定的 winner 解释为价值、因果质量、学习或永久写入授权。runtime/checkpoint schema 与默认 bootstrap 均不变。

## v0.139：Stage 3C-25 Winner Basin Margin 与 Opportunity 审计

Stage 3C-25 不修改 VM。它固定 Stage 3C-23 rank-two readout 和 Stage 3C-24 的 normalized-dot、threshold 0.8、latest/top-1 addressing，从 read-only control checkpoint 中逐 query 重建全部 eligible candidates，并精确复核 stored winner 与 similarity。

诊断把三个层次分开：

1. best-versus-second 的 absolute margin；
2. absolute margin 相对于该 query 全 eligible score spread 的 normalized margin；
3. 一个历史事件在 bounded delay window 中实际拥有的 eligibility opportunities，以及它跨不同 query 被重复选中的次数。

九 source 中 small absolute margin 普遍存在，但 reused winner 的 normalized margin 中位数在所有 source 都高于 single-use winner。Reused winner 也不是 exact query token 重复造成：每次复用都来自不同 query event 和不同 exact visible token。它们拥有更多 eligible opportunities，并形成跨多个 query tick 的 deterministic candidate basin。

该结果只定位 fixed-bootstrap addressing 的机会条件与 basin 结构。它不授权将较大 margin、更多 opportunity 或更高 reuse 解释为价值、因果正确性、学习、主体性或永久参数保留。


## v0.140：Stage 3C-26 Historical Age / Query Phase Opportunity 审计

Stage 3C-26 固定 Stage 3C-23 rank-two readout、normalized-dot、threshold 0.8、latest/top-1、target/carrier、delta、exposure 与 rollback，仅从 read-only control checkpoint 重建候选机会和 winner。

每 source 的 128 个 request 中，16 个无候选，112 个完成 assignment；首批 16 个 assignment 只有一个候选，因此强制选择 source-boundary phase-zero event。移除这些 query 后，age-one 机会归一化 selection rate 仍在所有 source 中最高或并列最高。reused winner 更早，但其 selection/opportunity 也仍不低于 single-use winner，说明 raw opportunity 不是完整解释。

该结果仅定位 fixed-bootstrap addressing 的边界与近因偏置，不给历史年龄赋值，不授权 reward、learned weights、permanent retention、learning、subjecthood 或 universal attention claim。


## v0.141：Stage 3C-27 Token 轨迹运动学审计

Stage 3C-27 固定 Stage 3C-23 rank-two readout、normalized-dot、threshold 0.8、latest/top-1、target/carrier、delta、exposure 与 rollback，只从 read-only control checkpoint 重建候选与局部 visible-token 轨迹。

九 source 的 864 个多候选 query 中，387 次选择 age one；386 次是严格 score geometry 胜出，只有 1 次依赖 exact latest tie-break。strict age-one query 的局部 normalized-token step 中位数约比 older-winner query 小 200 倍。第一 readout 坐标保持时 age one 几乎总被选择，发生变化时 winner 通常回到更早的同坐标状态。

该结果只定位 fixed-bootstrap readout 的采样几何和 recurrent basin，不给近因、速度、曲率或坐标状态赋值，不授权 reward、learned weights、permanent retention、learning、subjecthood 或 universal attention claim。
