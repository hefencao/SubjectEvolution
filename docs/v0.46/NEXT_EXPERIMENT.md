# Next experiment

The supplied D2-G result has already been reassessed by v0.46 and the 120-tick D2-H plan is included in this project.

## 1. Execute the 120-tick screen

```bash
se-d2-source-causal \
  --plan docs/v0.46/D2H_SOURCE_POPULATION_CAUSAL_PLAN.json \
  --output analyses/d2h_source_population_causal_120 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

The plan references the existing user-local D2-G final checkpoints under:

```text
/home/unkloser/projects/SubjectEvolution/analyses/d2g_source_population_burnin/execution/...
```

## 2. Assess the screen

```bash
se-d2-source-causal-assess \
  --results analyses/d2h_source_population_causal_120/d2_source_population_causal_results.json \
  --output analyses/d2h_source_population_causal_assessment_120
```

When the screen passes, the assessor writes:

```text
analyses/d2h_source_population_causal_assessment_120/
  d2_source_population_causal_confirmation_plan.json
  d2_source_population_causal_confirmation_plan.md
```

## 3. Execute confirmation only when generated

```bash
se-d2-source-causal \
  --plan analyses/d2h_source_population_causal_assessment_120/d2_source_population_causal_confirmation_plan.json \
  --output analyses/d2h_source_population_causal_300 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

Then compare horizons:

```bash
se-d2-source-causal-assess \
  --short-results analyses/d2h_source_population_causal_120/d2_source_population_causal_results.json \
  --long-results analyses/d2h_source_population_causal_300/d2_source_population_causal_results.json \
  --output analyses/d2h_source_population_causal_persistence
```

Copy number remains blocked regardless of this run's outcome.
