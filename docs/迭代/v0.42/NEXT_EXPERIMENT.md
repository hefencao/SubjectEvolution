# v0.42 next experiment

Run the initial 120-tick lineage-balanced matrix from the same 300-tick D2-B
source checkpoints, prioritizing modules 2 and 3:

```bash
se-d2-lineage-pairs \
  --results analyses/d2b_module_audit_300/d2_module_audit_results.json \
  --output analyses/d2d_lineage_pairs_120 \
  --modules 2,3 \
  --horizon 120 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

Before interpreting the result, verify that each checkpoint is eligible with at
least three lineages of eight or more living members. Ineligible checkpoints are
reported and skipped rather than padded or diversity-protected.

Continue to 300 ticks only when the output-routing effect, not merely the cost
refund or total expression contrast, repeats across at least two seeds and
multiple non-dominant lineage pairs. A result confined to one lineage or one
checkpoint remains lineage-background evidence.
