# Design

## Observation from D1-P

All formal seeds passed the minimum turnover health gate, but final population
was also the peak population in every seed: 876, 715, and 1025 entities from an
initial 128. Effective founder lineages were 4.01, 9.89, and 12.39. The panel is
valid wiring and turnover evidence, but not an equilibrium sample for deciding
which inherited coordinates need adjustment.

The original absolute persistence screen was insensitive to continuous-coordinate
contraction. A relative cross-seed reclassification finds 6 strong-thinning and
66 moderate-thinning coordinates, but active expansion and lineage concentration
block any gene-specific adjustment.

## Shared physical intervention

Change only `environment.resource_regeneration`, uniformly:

```text
[0.027, 0.027, 0.027, 0.027] -> [0.00675, 0.00675, 0.00675, 0.00675]
```

This reduces external material throughput without adding rewards, protecting a
gene, changing channel identities, or assigning ecological roles. Exploratory
seeds selected the candidate and are excluded from formal qualification.

## Cycle-aware qualification

The environment contains explicit periods 173, 240, 257, 311, 349, 419, and 431
ticks. A generic three-window audit at the 30-tick reporting cadence spans only
90 ticks and can mistake one environmental phase for a secular trend. D1-Q
therefore requires at least `ceil(max_environment_period / reporting_interval) +
1` observations, so first-to-last span covers a complete longest forcing cycle.

The cycle window must keep population between 0.5 and 2.0 times the initial
population, CV at or below 0.15, absolute normalized slope at or below 0.02 per
sample, and peak-to-trough envelope at or below 0.50 of the mean. Turnover,
descendant replacement, lineage breadth, and heritable-diversity checks remain
separate final-state requirements. Short three-window rebound/decline is retained
as advisory evidence rather than discarded.

## Frozen pilot

Seed 96032 reaches tick 840 without warning, hard-stop, or early exit. It was
executed only after the cycle-aware gate was frozen, and it passes the registered
source health contract and the cycle-aware qualification. The
frozen lock binds the exact config, runtime summaries, event stream, progress,
health report, equilibrium report, and file hashes.

## Qualification order

1. Freeze and audit D1-P evidence.
2. Generate a config whose only scientific change is shared regeneration.
3. Select the shared-flux candidate on exploratory seeds.
4. Qualify one new independent pilot with health and full-cycle equilibrium gates.
5. Freeze the pilot and authorize three disjoint independent panel seeds.
6. Require minimum health and cycle-aware equilibrium in every panel seed.
7. Run whole-genome relative retention screening.
8. Diagnose only repeated block-level or severe signals; do not generate a
   per-coordinate experimental portfolio.
