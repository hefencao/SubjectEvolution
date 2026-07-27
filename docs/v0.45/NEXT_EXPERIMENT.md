# Next experiment

The plan generated from the supplied D2-F assessment and trajectory is stored at:

```text
analyses/d2g_source_population_plan/d2_source_population_plan.json
```

Generate it again from the original files if paths need refreshing:

```bash
se-d2-source-population \
  --assessment analyses/d2f_lineage_mediation_assessment/d2_lineage_mediation_assessment.json \
  --mediation-results analyses/d2f_lineage_mediation_trajectory/d2_lineage_mediation_results.json \
  --output analyses/d2g_source_population_plan
```

Execute all six panels and both paired initial-condition arms:

```bash
se-d2-source-population \
  --plan analyses/d2g_source_population_plan/d2_source_population_plan.json \
  --output analyses/d2g_source_population_burnin \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

Assess the final unprotected burn-in populations:

```bash
se-d2-source-population-assess \
  --results analyses/d2g_source_population_burnin/d2_source_population_results.json \
  --output analyses/d2g_source_population_assessment
```

Do not change module copy number after plan generation or tick-zero equalization alone. If the source population qualifies, freeze the generated 600-tick checkpoints and first rerun the existing module-3 output/cost neutralization on those shared checkpoints.
