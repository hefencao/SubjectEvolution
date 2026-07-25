# v0.16 Long-run Evolution Diagnostics

## Purpose

v0.15 activated additional environmental and morphology dimensions.  The next
scientific question is no longer whether the mechanism executes, but whether
those dimensions remain under selection across long horizons and several
seeds.  v0.16 therefore adds observational diagnostics without changing policy,
knowledge routing, environment fields, lifecycle commits, or costs.

The diagnostics are opt-in:

```json
{
  "run": {
    "long_run_diagnostics_enabled": true,
    "long_run_diagnostics_schema": "long-run-evolution-diagnostics-v1"
  }
}
```

When disabled, archived `evolution_progress.jsonl` fields retain their v0.15
schema.

## Lineage and group alignment

Every evaluation window records:

- grouped entity count and fraction;
- current group count;
- lineage/group normalized mutual information;
- weighted group-lineage and lineage-group purity;
- `P(same lineage | same group)`;
- `P(same group | same lineage)`;
- pair enrichment over statistical independence.

NMI and purity are not interpreted alone.  High-cardinality lineage labels can
produce a large NMI even when no group is dominated by one lineage.  Pairwise
rates make this visible.  For example, one 120→150 continuation produced NMI
`0.749`, group-lineage purity `0.158`, and only `2.56%` same-lineage pairs within
same-group pairs, while the latter was still about `18.3×` the independence
baseline.  The appropriate reading is enrichment, not identity between groups
and genetic lineages.

## Window selection differentials

For active morphology traits the tracker accumulates three cohorts:

1. reproduction-eligible carrier ticks;
2. accepted parents;
3. committed offspring.

It publishes population-independent observational contrasts:

```text
successful-parent mean - eligible-carrier mean
committed-offspring mean - successful-parent mean
```

The first is a selection differential among eligible carriers.  The second
contains inheritance, mutation, clipping and finite-sample effects.  Neither is
fed back into reproduction or policy.

## Knowledge root lineages

Active copies are reduced to unique `(holder, root-content)` presences so that
several variants of one root in the same holder do not inflate prevalence.
Diagnostics include:

- active root-content count;
- effective root-content count;
- largest root holder share;
- fraction of roots spanning several genetic lineages or groups;
- root/genetic-lineage and root/group NMI;
- pairwise spread and enrichment measures.

These fields test whether cultural/knowledge diversity persists when founder
lineages concentrate.  A high NMI alone is not treated as evidence of causal
control or subjecthood.

## Mortality and birth pressure

The progress record adds descriptive window ratios:

```text
mortality_pressure = deaths / (end_alive + deaths)
birth_pressure = births / end_alive
```

They are intended for phase alignment and offline analysis, not as rewards or
controllers.

## Checkpoint semantics

Trait cohort sums and counters are stored inside the existing checkpointed
`EvolutionProgressTracker` state.  Full checkpoint restore therefore continues
selection windows exactly.  Group alignment and knowledge-lineage metrics are
recomputed from authoritative world state at each scheduled evaluation.

## Scientific limits

- Correlation between mortality and cohesion does not prove an intentional
  “huddle for warmth” mechanism.
- Correlation between lineage diversity and cohesion does not establish that
  genetic competition causes group boundaries.
- Pair enrichment reports overlap, not agency.
- Multi-seed repetition supports robustness, not inevitability.
- Causal claims still require same-checkpoint interventions.
