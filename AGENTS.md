# AGENTS.md

These rules apply to every automated or human-assisted change in this repository.
They are mandatory project contracts, not suggestions.

## 1. Baseline and execution

1. Use the explicitly supplied project archive as the only code baseline.
2. Do not replay old patches, reuse an earlier worktree, or reconstruct missing code
   from memory.
3. Perform actual source/document changes and validation; do not return only a plan.
4. Use the activated Conda editable environment. Run `make conda-sync` only after
   changing console entries, dependencies, package structure, or `pyproject.toml`.
5. Routine validation is `make test` and `make conda-check`. The independent native
   `src/gui/` workspace is outside Python freshness scanning; `src/se/gui/` is not.
6. In chat, report validation only when an actual non-GPU error remains. Keep complete
   validation reports inside the delivered evidence bundle.
7. Deliver only three top-level artifacts unless the user explicitly requests more:
   complete project archive, baseline-to-current patch, and research/evidence bundle.

## 2. Task type must be declared first

Before editing code or durable project documents, classify the iteration and write
one Git title using this exact form:

```text
[TYPE] scope: imperative summary
```

Allowed types:

- `[MAIN-EXP]` — the currently authorized mainline scientific experiment;
- `[BRANCH-EXP]` — an alternative or competing experimental mechanism;
- `[PARAM-EXP]` — code-parameter exploration or sweep;
- `[EVOLVE-ENV]` — evolution code that changes environment, substrate, ecology, or
  persistent selection opportunity;
- `[EVOLVE-SUBJECT]` — evolution code that changes subject capability, graph,
  genetics, development, inheritance, or costs;
- `[ENGINEERING]` — runtime, performance, tests, packaging, tooling, or refactor;
- `[DOC-GOV]` — documentation structure, governance, or task-tree maintenance;
- `[RELEASE]` — release assembly only.

Examples:

```text
[MAIN-EXP] D1-Z: audit action and objective-event threshold crossings
[BRANCH-EXP] D1-Z: compare bounded allocator alternative
[PARAM-EXP] subject-vm: scan fixed delay bounds on a separate branch
[EVOLVE-ENV] substrate: add persistent orthogonal resource pressure
[EVOLVE-SUBJECT] graph: add costed topology mutation contract
[DOC-GOV] docs: reorganize active docs and typed task tree
```

`[BRANCH-EXP]` must use an additional Git branch. `[PARAM-EXP]` normally uses an
additional branch and may not silently redefine a frozen mainline protocol.
Environment or subject-capability code must never be labelled only as an experiment.

### 2.1 Git command delivery contract

Every delivered iteration, including `[MAIN-EXP]`, `[ENGINEERING]`, and `[DOC-GOV]`,
must use or present a dedicated iteration branch. The final chat response must include
one executable Git command block covering all of the following transitions:

1. switch to the baseline main branch;
2. create or switch to the typed iteration branch;
3. apply and stage the delivered patch;
4. commit with the exact declared Git title;
5. switch back to the main branch;
6. fast-forward merge the iteration branch;
7. create the annotated release tag.

Use these branch prefixes:

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

The command block must name the actual baseline-to-current patch, branch, commit title,
and version tag. Do not substitute a generic template. Patch application must never
use a bare filename. Every handoff first defines one project-external `PATCH_DIR` and
prefixes the actual patch filename with it. The directory is persisted with
`se-study config --set-patch-dir <directory>` whenever that command exists in the
baseline.

The iteration that first introduces `--set-patch-dir` is a bootstrap exception: its
baseline cannot call the new option before applying the patch. That handoff must define
`PATCH_DIR`, apply the prefixed patch, and then persist the setting immediately through
the patched source with `PYTHONPATH=src python -m se.cmd.study config --set-patch-dir`.
Subsequent iterations configure or confirm the directory before patch application.
When no operator-specific path is known, use these executable shapes:

```bash
# Bootstrap iteration that introduces --set-patch-dir
PATCH_DIR="../SubjectEvolution-patches"
git apply --index "$PATCH_DIR/<actual-baseline-to-current.patch>"
PYTHONPATH=src python -m se.cmd.study config --set-patch-dir "$PATCH_DIR"

# Later iterations
PATCH_DIR="../SubjectEvolution-patches"
se-study config --set-patch-dir "$PATCH_DIR"
git apply --index "$PATCH_DIR/<actual-baseline-to-current.patch>"
```

The final handoff replaces the placeholder with the actual delivered patch name. When
the user identifies a missing prior-round command block, provide that prior block
together with the current iteration commands. Do not include destructive reset,
forced checkout, or an assumed remote pull in the default handoff. This section is the
persistent cross-chat command-format authority; new sessions must read `AGENTS.md`
before preparing a handoff.

## 3. Typed progress tree

`docs/PROJECT_STATUS.md` must always contain separate branches for:

- `[MAIN-EXP]`;
- `[BRANCH-EXP]`;
- `[PARAM-EXP]`;
- `[EVOLVE-ENV]`;
- `[EVOLVE-SUBJECT]`;
- `[ENGINEERING]`;
- `[DOC-GOV]`.

Each active item must be marked `NEXT`, `ACTIVE`, `BLOCKED`, `PARKED`, `FROZEN`, or
`DONE`. Do not mix test/release details into the scientific branch. Do not append one
section per historical Stage 3C iteration.

## 4. Documentation placement

Do not write provisional or merely expected results into durable active documents.
Use this placement matrix:

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

Additional rules:

1. `ARCHITECTURE.md` may describe a mechanism only after implementation and contract
   validation. It must not contain per-version result narratives or next-step claims.
2. `SCIENTIFIC_ISSUES.md` contains only unresolved questions. Remove resolved
   chronology instead of appending another version heading.
3. `PROJECT_STATUS.md` is current state only. Historical stage results belong in a
   result ledger.
4. During execution, provisional interpretation stays in analysis artifacts or the
   current iteration note. Update durable documents only after the result is frozen.
5. When a result is frozen, summarize the complete run chain in one result ledger
   entry rather than copying the same narrative into architecture, issues, and status.
6. New long-term principles must be written into governance before delivery; they may
   not remain chat-only.

## 5. Experiment governance

- Do not preassign reward or fixed value to objective coordinates.
- A mechanism requires explicit cost, ablation, and shared-checkpoint control.
- Independent source checkpoint is the primary replicate; entities/windows/events are
  not additional independent samples.
- Distinguish manipulation failure, support failure, identity/export failure, and a
  genuine small or path-dependent effect.
- Do not loosen thresholds, extend exposure, select seeds, or change horizon after
  observing results unless a new typed protocol is declared.
- No automatic keep/revert, learned weight, permanent retention, or subjecthood claim
  is authorized without a separate contract.

## 6. Release gate

Before delivery:

1. run full tests, configuration validation, editable/Conda verification, patch replay,
   and clean archive validation;
2. ensure the patch includes new and binary files;
3. compare the replayed tree with the target tree file by file;
4. verify archive and manifest hashes;
5. place detailed validation output in the evidence bundle;
6. report only remaining actual errors in chat.
