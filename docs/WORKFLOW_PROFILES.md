# Workflow profiles

This document owns validation, packaging, and handoff depth. `AGENTS.md` owns repository
invariants and requires choosing one profile, but it intentionally does not force the
largest profile on every change.

## 1. Profile selection

| Profile | Use when | Required outputs |
|---|---|---|
| `SCOPED-FIX` | Small documentation, test, or localized code correction with no frozen scientific claim | changed-scope checks and a concise change record |
| `STANDARD-CODE` | Product/runtime/tooling change spanning a module or public CLI | targeted tests, impacted integration tests, configuration/import checks |
| `SCIENTIFIC-FREEZE` | A preregistered experiment is run and a result is frozen | complete study chain, evidence integrity, reproducibility, frozen result ledger |
| `RELEASE-HANDOFF` | A versioned project archive and patch are delivered | release validation, patch replay, clean archive, hashes and handoff commands |

Profiles compose. A scientific release normally uses both `SCIENTIFIC-FREEZE` and
`RELEASE-HANDOFF`. A small local fix may use only `SCOPED-FIX`.

The project does not currently infer whether the operator intends to handle packaging
locally. Until that policy is explicitly decided, record the chosen profile instead of
inventing a local-only or release requirement.

## 2. `SCOPED-FIX`

Required:

1. declare the typed Git title and branch;
2. inspect the direct callers, tests, and documentation contract affected by the change;
3. run focused tests or static checks covering the changed boundary;
4. update active documentation only when its current contract changed;
5. provide branch and commit commands.

Not automatically required:

- full test sharding;
- Conda editable verification;
- parity;
- patch replay;
- clean archive generation;
- release tag.

Escalate to `STANDARD-CODE` when the change alters a public command, package entry point,
configuration schema, checkpoint format, or shared runtime behavior.

## 3. `STANDARD-CODE`

Includes all `SCOPED-FIX` steps plus:

1. run `make conda-sync` when console entries, dependencies, package structure, or
   `pyproject.toml` changed;
2. run the targeted module tests and all directly impacted integration/contract tests;
3. validate configuration and import/entry-point ownership affected by the change;
4. run `make test` or the relevant complete shard set when the change touches shared
   infrastructure used broadly across the repository;
5. record any remaining actual error.

A standard code change still does not require scientific study reruns unless it changes
an executable scientific contract or invalidates frozen evidence.

## 4. `SCIENTIFIC-FREEZE`

Required:

1. preregister the manipulation, controls, costs, lineage and rejection gates;
2. execute the complete declared source panel without adaptive seed, threshold, horizon,
   or exposure changes;
3. run evidence-integrity and component-reproducibility assessments;
4. distinguish prerequisite failure from hypothesis failure;
5. summarize the full run chain once in `docs/results/`;
6. update the current status tree and active scientific issues without copying the full
   result narrative into architecture;
7. use the complete scientific validation commands defined by the study workflow.

## 5. `RELEASE-HANDOFF`

Required only for a versioned artifact handoff:

1. run the selected underlying code/science profile first;
2. run release-freshness and isolated distribution checks;
3. generate a patch that includes new and binary files;
4. replay the patch on the exact baseline and compare the resulting tree file by file;
5. create a clean archive excluding ignored workspace settings and generated outputs;
6. verify archive, manifest and artifact hashes;
7. provide the actual branch, patch application, commit, fast-forward merge and annotated
   tag commands;
8. deliver the project archive, baseline-to-current patch and one evidence/result bundle
   unless a different artifact set was requested.

Passing validation is retained in files rather than expanded in chat. Only actual
remaining non-GPU errors are reported directly.
