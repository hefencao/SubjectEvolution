# Next experiment

Generate the plan from the completed D2-E assessment and the original 300-tick confirmation plan:

```bash
se-d2-lineage-mediate \
  --assessment analyses/d2e_lineage_pair_persistence/d2_lineage_pair_assessment.json \
  --source-plan analyses/d2e_lineage_pair_assessment/d2_lineage_pair_confirmation_plan.json \
  --output analyses/d2f_lineage_mediation_plan
```

The supplied-result plan has module 3, six checkpoints and 24 preserved checkpoint-lineage pairs.

Execute it:

```bash
se-d2-lineage-mediate \
  --plan analyses/d2f_lineage_mediation_plan/d2_lineage_mediation_plan.json \
  --output analyses/d2f_lineage_mediation_trajectory \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

Assess the result:

```bash
se-d2-lineage-mediate-assess \
  --results analyses/d2f_lineage_mediation_trajectory/d2_lineage_mediation_results.json \
  --output analyses/d2f_lineage_mediation_assessment
```

Do not extend module copy number after a mean-energy result alone. Continue only according to the generated mediation classification, and retain the existing source-lineage guard.
