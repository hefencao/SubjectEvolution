# SubjectEvolution project charter

Revision: **2**
Normative review: **v0.154**
Role: long-lived scientific mission, scope, and non-negotiable evidence boundaries.

This charter is intentionally independent of the current experiment number. Current work,
open questions, frozen results, and implementation details belong in the documents listed in
Section 12.

## 1. Mission

SubjectEvolution builds a large-scale, evolvable, intervenable, and reproducible simulation
for studying how physical carriers, heritable structures, ecological differentiation, social
organization, institutions, information structures, and nested candidate subjects may arise,
compete, persist, merge, split, and shift under existence constraints.

The project does not assume that an entity row, body, lineage, ecological type, group,
institution, or information template is automatically a subject. Each is only a candidate
structure. Persistence, causal control, continuation boundaries, and counterfactual effects
must be established from trajectories and interventions.

The durable research questions are:

1. Can multidimensional physical constraints select stable and heritable differentiation?
2. Can differentiated carriers occupy distinct niches and create competition, complementarity,
   dependence, parasitism, or symbiosis?
3. Can ecological and informational constraints generate persistent social organization?
4. Can higher-level structures preserve state and exert causal control beyond a simple sum of
   members?
5. Can continuation, control, and maintenance boundaries move among bodies, lineages, groups,
   institutions, and information structures?
6. How do observation, finite capacity, metabolism, implementation choices, and experimental
   design limit those conclusions?

## 2. Primary causal programme

The main programme follows this ordering:

```text
multidimensional environment and temporal forcing
→ heritable variation, expression, and capacity allocation
→ embodied trait differentiation
→ niche formation and ecological relations
→ information demand, complementarity, and dependence
→ social organization and higher-level candidate subjects
→ nested control and subject-boundary shift
```

Environment and ecological differentiation are prerequisites, not decorative context. Until
those layers have qualified evidence, complex social controllers, general recursive subject
structures, and agent-level reinforcement learning are not the default mainline.

## 3. Ontology and evidence layers

### 3.1 Physical structures and candidate subjects are distinct

The project maintains separate concepts for:

- physical entities, bodies, resources, terrain, links, and facilities;
- candidate subjects, membership, lineage, control, dependence, replication, overlap, and
  nesting.

Physical row ID, entity ID, group label, ecological label, lineage label, and subject ID must
not be treated as interchangeable.

### 3.2 Objective facts are not value

The world records objective processes and consequences. It does not label resource receipt,
prediction accuracy, protection, reproduction, injury, cooperation, or conflict as internally
positive or negative.

External scientific analyses may estimate continuation effects, for example by paired
intervention:

\[
I_X(a,H)=P(P_X(t+H)>0\mid do(a))-P(P_X(t+H)>0\mid do(a_{baseline}))
\]

This is an observer-side operational quantity. It is not permission to inject reward, utility,
trust, loyalty, hostility, knowledge value, or a scalar subjecthood score into the runtime.

### 3.3 Five causal stages remain separate

Every claim must distinguish:

1. objective world state;
2. information available to a candidate structure;
3. control or action proposal;
4. executed physical action and settlement;
5. later evaluation of ecological, continuation, or control effects.

A later consequence cannot validate its own initiating action in the same causal phase.

## 4. Fixed world kernel and evolvable structures

The world kernel defines versioned physical interfaces, conservation rules, observation ports,
actuator ports, conflict settlement, and generic operators. Runtime code generation and
per-entity custom kernels are outside the main design.

Within that kernel, evolution may alter heritable parameters, expression, routing, capacity,
module copy number, development, topology where authorized, and lifecycle state.

A fixed kernel is an explicit modelling prior. It must be documented, ablated when relevant,
and reflected in the scope of every conclusion.

## 5. Environment and ecological qualification

### 5.1 Effective environmental diversity

Environmental diversity is not the number of resource fields. Qualified diversity requires
constraints that cannot all be solved by one scalar strategy. Useful axes may differ in:

- spatial generation and correlation length;
- temporal cycle, phase, diffusion, and dissipation;
- storage versus immediate use;
- movement, exposure, repair, and defence trade-offs;
- observation and communication media;
- conversion chains, by-products, and local infrastructure;
- non-substitutable materials or opportunities.

Independent fields may be positively correlated, negatively correlated, or nearly independent
in a particular configuration. No universal terrain, danger, or signal scalar is assumed.

### 5.2 Environment gate before ecological or social claims

Before interpreting differentiation, niches, or social function, the environment must show:

- persistent nontrivial variation on relevant spatial and temporal scales;
- viable turnover and replacement rather than a temporary founder rebound;
- real material, informational, or processing constraints;
- opportunity for more than one sustainable strategy without diversity subsidies;
- robustness across independent source histories appropriate to the claim.

A single source may debug shared physical parameters. It cannot by itself authorize a frozen
selection, ecological, social, or subjecthood conclusion.

### 5.3 Physical value chain before role claims

A repeated action or analyst-assigned label is not a function. A role-like claim requires a
role-neutral chain:

```text
physical pressure or trade-off
→ observable signal
→ transmission or persistence path
→ actionable receiver interface
→ measurable downstream consequence
```

Each link must exist without role reward, group privilege, or genotype-specific subsidy.

## 6. Evolvable carriers, modules, and capacity

### 6.1 Embodied differentiation

A heritable difference counts as scientific differentiation only when it:

- is expressed or otherwise persists;
- changes physical capacity, behaviour, or world interaction;
- incurs cost or opportunity cost;
- produces reproducible ecological consequences;
- survives appropriate neutralization, ablation, or environment reversal tests.

Unused genes, inert module slots, parameter variance, and designer labels are not sufficient.

### 6.2 Modular structure

The implementation may provide bounded module slots containing generic inputs, operators,
routing, expression gates, outputs, capacity budgets, provenance, development, damage, and
repair state. Module names must remain role-neutral.

Generic operators cannot bypass feasibility masks, conservation, resource accounting, signal
propagation, arbitration, ownership, or physical settlement.

### 6.3 Structure, expression, use, and cost are separate

For every evolvable capability, distinguish:

- inherited structure;
- developmental construction;
- current expression;
- active capacity;
- actual use;
- structural maintenance cost;
- execution cost;
- development and reproduction cost;
- material, mass, space, or opportunity cost.

A single uncalibrated complexity tax must not stand in for all of these.

### 6.4 Healthy turnover and capability affordability

A new capability must not charge random founders the full cost of a mature multi-gene
combination before the combination can function. Capability studies require a qualified
carrier substrate, an explicit maturation window, separate cost accounts, and a failure mode
that stops before causal or evolutionary interpretation when the carrier collapses.

The observation window for long-term qualification must cover the longest relevant external
forcing period. A short phase-specific decline or rebound cannot by itself establish or reject
steady behaviour.

## 7. Cognitive and Subject Graph architecture policy

The project may prescribe a general cognitive substrate because discovering every possible
cognitive architecture is not the research target. Allowed priors include bounded regions,
state retention, causal update phases, generic operators, routing costs, eligibility traces,
and developmental accessibility.

It must not prescribe concrete cognition such as fixed interests, semantic benefit channels,
friend/enemy classes, trust rules, knowledge value, social roles, or group obedience.

The current direction is a unified Subject Graph VM with shared node and edge identity and
initially biased regions. Region labels are engineering priors, not evidence that a region
contains memory, attribution, interest, policy, language, leadership, or any other named
cognitive function.

Detailed current semantics are owned by `docs/PARTITIONED_SUBJECT_GRAPH_VM.md` and the
machine-readable decision protocols.

## 8. Candidate subjects and epoch boundaries

Candidate subjects may include bodies, lineages, module lineages, persistent ecological
relations, groups, shared facilities, institutions, and information templates. Advancement to
an active candidate requires evidence such as persistent state, boundary continuity, control
contribution, intervention sensitivity, or continuation across carrier replacement.

The programme uses evidence epochs rather than reward stages:

- **Epoch 0 — ecological carriers:** physical, ecological, informational, and relational
  structures may be studied without subjecthood claims.
- **Epoch 1 — entity-subject candidates:** delayed consequences and persistent internal
  organization may influence future action across replacement and independent sources.
- **Epoch 2 — group-subject candidates:** group-owned state or rules persist across member
  turnover and causally constrain group-level continuation or control.

An epoch name is an evidence boundary. It is not a runtime identity, policy hint, reward, or
controller.

## 9. Scientific inference standards

### 9.1 Replication unit and sample adequacy

The ordinary replicate unit is the independently generated source checkpoint or another
predeclared independent world history. Entities, events, windows, coordinates, and ticks within
one source are dependent observations, not extra independent replicates.

The charter does not prescribe one universal seed count. Exploratory, calibration, mechanism,
and frozen inference studies have different support needs. Each frozen protocol must justify
its panel size, rejection gates, paired structure, and the strength of conclusion it permits.

### 9.2 Required causal controls

A mechanism-level claim normally requires:

- explicit manipulation and neutralization;
- cost accounting where the mechanism is costly;
- shared-checkpoint paired controls where applicable;
- branch, configuration, and lineage identity verification;
- support and exposure checks;
- component-wise reporting without undeclared scalarization;
- failure rates and source-balanced summaries;
- a distinction among manipulation failure, prerequisite failure, export/identity error,
  path-dependent effect, and replicated effect.

Thresholds, source panels, horizons, exposure, and interpretation gates cannot be relaxed after
observing results unless a separately typed protocol is declared.

### 9.3 No automatic promotion from correlation

The following are never sufficient on their own:

- gene or parameter variance;
- more modules or capacity;
- survival of high-capacity entities;
- one cluster or one interesting trajectory;
- group-label persistence;
- environment-lineage correlation;
- score margin, attention rank, association identity, or internal update route;
- analyst names such as scout, guard, leader, organ, institution, or memory.

## 10. Programme stages

The durable programme stages are:

- **D0 — environmental axis qualification**;
- **D1 — capacity, carrier, and Subject Graph substrate differentiation**;
- **D2 — generic module expression and routing**;
- **D3 — duplication, deletion, and functional novelty**;
- **D4 — niche formation and ecological coexistence**;
- **D5 — social organization and higher-level control**;
- **D6 — subject-boundary shift and nesting**.

These are scientific programme categories, not an append-only implementation timeline. Current
subtasks and their status belong in `docs/PROJECT_STATUS.md`.

## 11. Non-goals

The current programme does not seek to:

- simulate consciousness directly;
- create unbounded new physics through runtime code generation;
- reward complexity, diversity, roles, groups, or subjecthood;
- protect multiple strategies by design;
- collapse component evidence into one subjecthood score;
- treat backend-specific wiring as a scientific mechanism;
- grant permanent retention from a temporary or mixed-direction effect;
- expand social control before ecological and lower-level causal prerequisites exist.

## 12. Document authority

| Question | Authority |
|---|---|
| Why the project exists and what it may claim | `PROJECT_CHARTER.md` |
| Cross-version evidence and process rules | `PROJECT_GOVERNANCE.md` and `AGENTS.md` |
| Current system structure | `ARCHITECTURE.md` |
| Current Subject Graph VM mechanism semantics | `PARTITIONED_SUBJECT_GRAPH_VM.md` and `protocols/decisions/` |
| Current typed work tree | `PROJECT_STATUS.md` |
| Active unresolved scientific questions | `SCIENTIFIC_ISSUES.md` |
| Frozen validated results | `docs/results/` |
| Version history | `CHANGELOG.md` |
| Current iteration work record | `docs/迭代/` |

When these documents conflict, the more specific executable protocol controls the experiment;
the charter controls allowed project-level interpretation. A current status entry or iteration
note cannot silently amend this charter.
