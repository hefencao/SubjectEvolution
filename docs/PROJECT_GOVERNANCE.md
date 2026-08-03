# SubjectEvolution project governance

Role: durable cross-version rules for selecting, executing, freezing, documenting, and handing
off work. Task-specific command depth is owned by `docs/WORKFLOW_PROFILES.md`; repository-wide
agent rules are summarized in `AGENTS.md`.

## 1. Governance cycle

Every iteration performs one lightweight governance check:

1. **Expectation check:** Does the observed result differ from the preregistered expectation?
2. **Root-cause check:** Is the difference caused by manipulation, support, identity/export,
   observation coverage, source health, or a genuine scientific effect?
3. **Task check:** Should the current task continue, stop at a prerequisite, or be retyped?
4. **Principle check:** Did the work reveal a durable rule or modify an existing one?
5. **Documentation check:** Is any durable rule still present only in chat or an iteration note?

A surprising result is not automatically a reason to change the mechanism. A failed
prerequisite is not a failed downstream hypothesis.

## 2. Typed work and branch discipline

Every change has one primary type and Git title:

```text
[TYPE] scope: imperative summary
```

Scientific mainline, alternative branches, parameter exploration, environment evolution,
subject-capability evolution, engineering, documentation governance, and release assembly are
separate work classes. A code change that alters the environment or evolvable subject cannot
be hidden inside an ordinary experiment label.

Competing experiments and parameter exploration use separate branches unless an explicit
reason is recorded. A frozen mainline protocol is never silently redefined by exploratory
work.

## 3. Environment maturity before genetic or social inference

Environment construction precedes selection and social interpretation. Before a source can
support those claims, it must satisfy the relevant predeclared gates for:

- viable population and turnover;
- generation depth and founder replacement;
- physical heterogeneity and opportunity;
- relevant material or informational dependencies;
- observation coverage across the longest configured forcing period.

A single source can debug shared environment parameters. It cannot authorize a frozen genetic,
ecological, social, or subjecthood conclusion.

A population rebound after a deep bottleneck does not by itself restore source qualification;
lineage breadth and replacement must also be assessed.

## 4. Integration-first capability development

When a healthy substrate already contains several mechanisms and environment axes, first study
the integrated system. Do not automatically create one environment, candidate ledger, or paired
experiment for every gene.

Use bounded multi-generation panels to identify which capabilities are absent, unused,
mis-costed, unsupported by the environment, or lost before maturation. Only then alter shared
interfaces, developmental timing, cost budgets, or physical opportunity.

Health gates qualify the carrier substrate. They do not select a preferred capability or prove
adaptation.

## 5. Manipulation, exposure, and observation

A causal manipulation must prove that it actually occurred. Required checks may include:

- the intended target and route changed;
- the control reserved matching budget without changing state;
- branch random streams and source identities remained aligned;
- realized dose and duration matched the declaration;
- rollback or finalization completed as required;
- the observation window covered the possible downstream effect.

For exposure studies, distinguish:

1. live-ledger dose;
2. common evaluation support;
3. observation coverage.

If changing exposure changes which windows finish before export, rollback-complete windows
cannot serve as the primary propagation estimator without a common-support correction.

## 6. Replication and inferential identity

The primary ordinary replicate is an independent source checkpoint or another preregistered
independent world history. Events, entities, windows, coordinates, and ticks within a source
are dependent evidence.

Frozen inference requires explicit identities for:

- normalized configuration;
- source checkpoint and authoritative state hash;
- branch role and paired family;
- random-stream policy;
- manipulation policy;
- export schema and finalization state;
- assessment version and input checksums.

A study may stop at a prerequisite gate. In that case, the downstream prediction is untested,
not supported and not refuted.

## 7. Candidate and portfolio boundaries

Exploratory analyses may identify candidate mechanisms, parameter regions, source families, or
measurements. Candidate discovery does not authorize selective confirmation on the same data.

When multiple candidates exist:

- record the full candidate set and selection rule;
- separate calibration sources from inference sources;
- freeze the chosen candidate before the independent panel;
- retain failed and null sources in the evidence bundle;
- do not promote one successful coordinate, seed, or branch into a general mechanism claim.

## 8. Subject Graph VM governance

### 8.1 Architecture prior versus concrete cognition

The project may fix bounded regions, routing phases, generic operators, state capacity,
eligibility, provenance, and costs. It may not encode semantic benefit ledgers, fixed reward,
trust, hostility, group identity, knowledge value, or role-specific policy as the answer.

### 8.2 Single routing ownership

When the Subject Graph VM owns the optional action-residual path, legacy knowledge, latent,
working-memory, and sparse-selection residual routes cannot coexecute as competing owners.
Legacy implementations may remain for old checkpoints, ablations, and fixed-cognition
baselines, but are not automatically migrated into Subject VM identity.

### 8.3 Bootstrap mechanisms

Fixed bootstrap attention, readout, and addressing are engineering shaping aids. Their score,
rank, margin, selected identity, or update route has no intrinsic value meaning. Historical
diagnostic bins must not be confused with runtime comparator semantics.

### 8.4 Temporary write boundary

Temporary writes require bounded target families, explicit delta limits, control reservation,
transaction identity, later-tick visibility, rollback, and export-boundary finalization.

No automatic keep/revert, learned weight, adaptive exposure, or permanent retention is allowed
without a separate protocol and stronger replicated evidence.

## 9. Frozen-result and workspace boundary

Generated analyses, checkpoints, result bundles, patch directories, and operator workspace
configuration remain outside the tracked project tree unless a compact frozen artifact is
explicitly admitted.

A frozen result must:

- bind its inputs by checksum and lineage;
- contain enough metadata to reproduce the run chain;
- include null, failed, and stopped branches;
- summarize component evidence without hidden scalarization;
- distinguish provisional interpretation from authorized conclusion.

`se-workspace` owns local result and patch directories. Study runners consume those settings
but do not own them.

## 10. Declarative study execution

Formal studies use versioned declarative workflows. Parameters have types, defaults, and
descriptions. Rendered commands must be inspectable before execution, and invocation must not
silently pass through a shell.

A workflow records prerequisite gates, source panel, branch plan, assessments, packaging, and
expected outputs. Changing the workflow after seeing results creates a new typed protocol.

## 11. Documentation authority

Active documents have non-overlapping roles:

| Content | Authority |
|---|---|
| Project mission and interpretation limits | `PROJECT_CHARTER.md` |
| Durable process and inference rules | `PROJECT_GOVERNANCE.md` and `AGENTS.md` |
| Current structural architecture | `ARCHITECTURE.md` |
| Current Subject Graph VM mechanism contract | `PARTITIONED_SUBJECT_GRAPH_VM.md` |
| Current typed task tree | `PROJECT_STATUS.md` |
| Active unresolved scientific questions | `SCIENTIFIC_ISSUES.md` |
| Frozen validated scientific results | `docs/results/` |
| Current iteration plan and work log | `docs/迭代/` |
| Executable experiment identity | `protocols/decisions/` and `studies/*/workflow.toml` |
| Delivered version history | `CHANGELOG.md` |

Provisional or expected results remain in analysis output or the current iteration note.
Architecture, charter, governance, status, and active issues are not version diaries.

When a result freezes, summarize the complete run chain once in the relevant result ledger.
Do not copy the same narrative into several active documents.

## 12. Workflow depth and handoff

Validation and delivery depth are selected from `docs/WORKFLOW_PROFILES.md`:

- `SCOPED-FIX` for localized corrections;
- `STANDARD-CODE` for shared code or public interface changes;
- `SCIENTIFIC-FREEZE` for formal experiment execution and result freezing;
- `RELEASE-HANDOFF` for archive, patch, replay, and transferability evidence.

Passing routine validation belongs in evidence files. Chat reports only actual remaining
non-GPU errors, scientific conclusions, and requested handoff commands.
