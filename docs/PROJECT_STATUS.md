# SE project status

Version: **0.100.0**

## Current scientific task

D1-R is formally closed as `threshold-not-reached`. All three seeds completed
tick 1800 and showed physical heterogeneity plus real within-group raw-resource
exchange, but the preregistered social-structure criterion was reproduced in
only two seeds:

- seed 97101: two persistent division-candidate group lineages;
- seed 97102: two persistent division-candidate group lineages;
- seed 97103: no lineage persistent across two windows.

The third seed also passed through a deep demographic bottleneck (42 alive from
128 initial), finished with about 3.03 effective founder lineages and had one
lineage represent about 44.3% of the final population. D1-R therefore does not
show a replicated environment capable of supporting multiple structured groups.
It authorizes neither gene audit nor adaptation, selection, niche, social-role
or subjecthood interpretation.

The active task is D1-S: increase the number and accessibility of independent
material-processing circuits while preserving role neutrality and total mean
material opportunity.

## D1-S shared physical change

D1-S keeps the complete inherited subject and all D1-R mechanisms unchanged. It
changes only two environmental geometry parameters:

1. the antipodal resource circuit weight rises from 0.35 to 0.55;
2. all source and processing province radii are uniformly scaled by 1.15.

Each resource-channel field is normalized after the primary and antipodal
circuits are combined. The global mean external material opportunity therefore
remains unchanged. No resource channel, recipe, exchange rule, group threshold,
gene, mutation rate, maintenance cost, reproduction rule, lineage protection or
role reward changes.

A completed exploratory seed at tick 900 showed viable turnover, strong physical
heterogeneity, real internal exchange, up to six simultaneous division
candidates and one persistent group lineage. It is frozen as
`parameter-debug-only`; it does not qualify the environment.

## Formal D1-S gate

Formal seeds are `100101,100102,100103`, each through tick 1800. Every seed must
satisfy all existing D1-R physical and group-division criteria plus:

- minimum recorded alive population / initial population >= 0.50;
- final effective founder lineages >= 4.0;
- at least two persistent division-candidate group lineages;
- at least two simultaneous division candidates in a diagnostic window;
- nonzero real within-group raw-resource exchange.

All three seeds must pass. Thresholds are fixed before formal execution and may
not be relaxed after observing results. A failed formal seed returns the project
to shared-environment debugging; it does not authorize a gene-level correction.

## Engineering changes

- `resource_province_secondary_weight` is configurable with a disabled-default
  compatibility value of 0.35.
- D1-S config generation can uniformly scale province radii and records both
  geometry changes in the manifest.
- `se-environment-structure-summary` can apply optional whole-run bottleneck and
  final lineage-breadth gates from `evolution_progress.jsonl`.
- Compact result bundles now include evolution progress, group windows, group
  summaries, environment-atlas rows/summaries, termination and scientific
  validity metadata by default.
- Frozen predecessor and parameter-debug files are verified by exact size and
  SHA-256 before D1-S config generation.
- D1-R historical workflow and evidence remain available, but its study status
  is closed and its formal-panel authorization is false.

## Authorization

Authorized:

- simple single-seed probes solely for debugging shared environmental geometry;
- one unchanged three-seed D1-S formal structured-environment panel;
- observational physical, demographic and group-structure summaries;
- external result packaging without checkpoints by default.

Not authorized:

- single-run or formal gene-retention audit;
- changing a gene because it is thin, rare or absent;
- paired mechanism experiments or candidate-ledger restart;
- genotype-, lineage-, group- or role-specific support;
- adaptation, selection, ecological-role, social-role, niche or subjecthood
  conclusions.
