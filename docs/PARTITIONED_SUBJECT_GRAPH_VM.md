# Partitioned Subject Graph VM v1

Status: **implementation contract frozen; runtime implementation not started**
Project version: **0.110.0**

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

### Stage 3B — local eligibility and delayed association (not implemented)

Future work may implement:

- short-lived local node/edge eligibility or another bounded local bridge;
- later-tick association between historical tokens and objective events;
- generic delayed update operators;
- unexplained residual through unassigned events;
- later-tick-only state changes;
- no fixed valence mapping.

Acceptance will require the same objective event to produce different future changes under different inherited graph parameters without changing event facts or persisting a whole-network path history.

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
