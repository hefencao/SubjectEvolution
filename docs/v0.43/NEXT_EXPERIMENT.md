# v0.43 next experiment

The supplied 120-tick D2-D result passes the module-level continuation screen for modules 2 and 3. Run the generated confirmation plan from the original source checkpoints:

```bash
se-d2-lineage-pairs \
  --plan analyses/d2e_lineage_pair_assessment/d2_lineage_pair_confirmation_plan.json \
  --output analyses/d2e_lineage_pairs_300 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

Then compare the 120- and 300-tick results:

```bash
se-d2-lineage-assess \
  --short-results analyses/d2d_lineage_pairs_120/d2_lineage_pair_results.json \
  --long-results analyses/d2e_lineage_pairs_300/d2_lineage_pair_results.json \
  --output analyses/d2e_lineage_pair_persistence
```

Do not copy modules after a positive 300-tick result while the source lineage guard still fails. A confirmed positive cross-lineage ecological effect would instead justify redesigning the source population or experimental start so the effective-lineage guard can be tested without artificial diversity protection.
