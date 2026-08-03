# SubjectEvolution v0.151.0

SubjectEvolution is an experimental simulation project for evolving subject-like
internal organization without preassigned reward or human social semantics.

Version 0.151.0 preserves the Stage 3C-35 preregistered disjoint-source
qualification failure while separating workspace configuration and validation workflow ownership. The new source panel does not reproduce the Stage 3C-27
geometry prerequisite required before Stage 3C-28; the Stage 3C-33/34 crossing
classifier is therefore not tested, refuted, or supported on this panel.

## Documentation map

- Current architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Typed task tree: [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)
- Active scientific issues: [`docs/SCIENTIFIC_ISSUES.md`](docs/SCIENTIFIC_ISSUES.md)
- Frozen Stage 3C results: [`docs/results/SUBJECT_VM_STAGE3C_RESULTS.md`](docs/results/SUBJECT_VM_STAGE3C_RESULTS.md)
- Subject Graph VM contract: [`docs/PARTITIONED_SUBJECT_GRAPH_VM.md`](docs/PARTITIONED_SUBJECT_GRAPH_VM.md)
- Repository agent rules: [`AGENTS.md`](AGENTS.md)
- Validation and handoff profiles: [`docs/WORKFLOW_PROFILES.md`](docs/WORKFLOW_PROFILES.md)

## Current scientific frontier

The original panel has 386/387 strict-geometry age-one selections; the disjoint
panel has 363/369. Exact latest-tie use rises from 1/864 to 6/864. Only seeds
12402 and 12408 satisfy all three per-source diagnostic thresholds. Stage 3C-28
correctly blocks the later chain, so no responsive-seed replacement or gate
relaxation is authorized.

The next mainline step is a read-only cross-panel decomposition of candidate
opportunity, first-state recurrence, and strict-geometry loss. It must not run a
new panel, alter addressing, or resume Stage 3C-33 until the transport failure is
understood.


## Workspace configuration

Operator-specific external directories are stored in the ignored `.se-workspace.toml`
and are owned by the dedicated workspace command:

```bash
se-workspace show
se-workspace config --set-result-dir <external-results-directory>
se-workspace config --set-patch-dir <external-patch-directory>
se-workspace path result
se-workspace path patch
```

`se-study` only renders and runs declarative study workflows; it no longer configures
operator workspace paths.
