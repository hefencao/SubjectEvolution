# Studies

A study directory is the canonical home for one scientific result chain.

Each study keeps its candidate specification, source configurations, design, ordered command files, and frozen evidence together. Runtime outputs do not live here:

- source trajectories and checkpoints: `runs/base/<study>/<stage>/`;
- intervention branches: `runs/interventions/<study>/<stage>/`;
- derived assessments and audits: `analyses/<study>/<stage>/`;
- mutable decision overlay: `state/decisions/`.

`se-study-freeze` copies compact plans, results, assessments, and decisions into `frozen/<stage>/`, binds legacy generic source plans by recorded content hash, and records canonical checkpoint destinations plus their hashes. `se-study-layout-migrate` splits a verified legacy stage into canonical source-run, intervention-run, and analysis roots. `se-study-runtime-migrate` can materialize checkpoint anchors alone when only recovery state is retained. `se-study-verify` validates the complete frozen chain without requiring the original project version or machine path.

README files are descriptive only. Exact executable steps belong in each study's numerically ordered `commands/` directory.
