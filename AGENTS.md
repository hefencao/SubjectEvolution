# AGENTS.md

These rules apply to every automated or human-assisted change in this repository.
They define repository invariants; task-specific validation and delivery steps live in
`docs/WORKFLOW_PROFILES.md`.

## 1. Baseline and task identity

1. Use the explicitly supplied project archive or checkout as the only code baseline.
2. Do not replay old patches, reuse earlier worktrees, or reconstruct missing code from memory.
3. Before editing, declare exactly one Git title:

```text
[TYPE] scope: imperative summary
```

Allowed types:

- `[MAIN-EXP]` — authorized mainline scientific experiment;
- `[BRANCH-EXP]` — competing or alternative experiment;
- `[PARAM-EXP]` — code-parameter exploration or sweep;
- `[EVOLVE-ENV]` — environment, substrate, ecology, or persistent pressure code;
- `[EVOLVE-SUBJECT]` — subject capability, graph, genetics, development, inheritance, or cost code;
- `[ENGINEERING]` — runtime, performance, tests, packaging, tooling, or refactor;
- `[DOC-GOV]` — documentation structure, governance, or task-tree maintenance;
- `[RELEASE]` — release assembly only.

`[BRANCH-EXP]` must use an additional Git branch. `[PARAM-EXP]` normally uses an
additional branch and may not silently redefine a frozen mainline protocol.
Environment or subject-capability code must never be labelled only as an experiment.

## 2. Workflow profile selection

Select one profile from `docs/WORKFLOW_PROFILES.md` before running validation or
preparing artifacts. `AGENTS.md` does not mandate a full release workflow for every
change.

- A small documentation or code fix may use a scoped profile.
- A frozen scientific result requires the scientific-freeze profile.
- Patch replay, clean archives, manifests, and release tags belong to the release-handoff profile.
- Do not silently upgrade a small fix into a full scientific/release cycle.
- Automatic inference of whether the user is working locally without needing artifacts is
  currently unresolved; do not encode a guessed rule as project policy.

Changing console entries, dependencies, package structure, or `pyproject.toml` still
requires the environment synchronization step defined by the selected workflow profile.

## 3. Git handoff contract

Every final chat response must include concrete Git commands appropriate to the selected
workflow profile. A branch and exact commit title are always required. Merge and tag
commands are included only when the iteration is delivered as a versioned handoff.

Branch prefixes:

| Type | Branch prefix |
|---|---|
| `[MAIN-EXP]` | `main-exp/` |
| `[BRANCH-EXP]` | `branch-exp/` |
| `[PARAM-EXP]` | `param-exp/` |
| `[EVOLVE-ENV]` | `evolve-env/` |
| `[EVOLVE-SUBJECT]` | `evolve-subject/` |
| `[ENGINEERING]` | `engineering/` |
| `[DOC-GOV]` | `docs/` |
| `[RELEASE]` | `release/` |

When a patch is delivered, never use a bare patch filename. The configured directory is
owned by `se-workspace`, not `se-study`. From versions that contain the command, use:

```bash
git apply --index "$(se-workspace path patch)/<actual-patch-name>"
```

Do not print a new `PATCH_DIR=...` assignment when the operator has already configured
the directory. Do not include destructive reset, forced checkout, or an assumed remote pull.

This section is the persistent cross-chat authority for Git command formatting.

## 4. Typed progress tree

`docs/PROJECT_STATUS.md` must keep separate branches for:

- `[MAIN-EXP]`;
- `[BRANCH-EXP]`;
- `[PARAM-EXP]`;
- `[EVOLVE-ENV]`;
- `[EVOLVE-SUBJECT]`;
- `[ENGINEERING]`;
- `[DOC-GOV]`.

Each active item uses `NEXT`, `ACTIVE`, `BLOCKED`, `PARKED`, `FROZEN`, or `DONE`.
Do not mix test, packaging, or workspace tooling into the scientific branch.

## 5. Documentation placement

Do not write provisional or expected results into durable active documents.

| Content | Required location |
|---|---|
| Current structural contract | `docs/ARCHITECTURE.md` |
| Current typed task tree | `docs/PROJECT_STATUS.md` |
| Active unresolved scientific question | `docs/SCIENTIFIC_ISSUES.md` |
| Frozen validated result | `docs/results/` |
| Current iteration design and work log | `docs/迭代/` |
| Durable process/inference rule | `docs/PROJECT_GOVERNANCE.md` and this file |
| Versioned delivered change | `docs/CHANGELOG.md` |
| Executable experiment identity | `protocols/decisions/` and `studies/*/workflow.toml` |

`ARCHITECTURE.md` is not a version diary. `SCIENTIFIC_ISSUES.md` contains unresolved
questions only. `PROJECT_STATUS.md` is current state only. Frozen results are summarized
once in `docs/results/` rather than copied into several active documents.

## 6. Scientific governance

- Do not preassign reward or fixed value to objective coordinates.
- A mechanism requires explicit cost, ablation, and shared-checkpoint control.
- Independent source checkpoint is the primary replicate; entities, windows, events,
  and coordinates are not additional independent samples.
- Distinguish manipulation failure, support failure, identity/export failure, and a
  genuine small or path-dependent effect.
- Do not loosen thresholds, extend exposure, select seeds, or change horizon after
  observing results unless a new typed protocol is declared.
- No automatic keep/revert, learned weight, permanent retention, or subjecthood claim
  is authorized without a separate contract.

## 7. Chat and artifact reporting

Report validation in chat only when an actual non-GPU error remains. Detailed logs belong
in the selected workflow's evidence output. Keep the user-facing discussion centered on
project code or experiment results rather than routine passing checks.
