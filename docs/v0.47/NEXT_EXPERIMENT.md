# Next experiment: D4-A 120-tick screen

Run the generated plan:

```bash
se-d4-niche-reversal \
  --plan docs/v0.47/d4_niche_reversal_plan.json \
  --output analyses/d4a_niche_reversal_120 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

Assess the result:

```bash
se-d4-niche-assess \
  --results analyses/d4a_niche_reversal_120/d4_niche_reversal_results.json \
  --output analyses/d4a_niche_reversal_assessment_120
```

Possible routes:

- `run-300-tick-d4a-niche-reversal-confirmation`: run the generated confirmation plan without removing any checkpoint-lineage pairs;
- `resource-affinity-or-geography-contrast-too-weak-redesign-d4-source`: the source phenotypes or the 180-degree resource contrast are too weak for this audit;
- `no-replicated-affinity-environment-interaction-stop-d4a`: source exposure exists, but inherited affinity does not causally condition the endpoint response.

Do not run further module-copy audits from the D2-H result.
