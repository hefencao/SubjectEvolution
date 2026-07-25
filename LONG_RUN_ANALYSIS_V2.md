# Long-run analysis v2

v0.16 reported raw within-run Pearson correlations. v0.17 retains those fields but adds three checks designed to expose shared temporal drift.

## Added statistics

1. **First differences**
   - delta mortality vs delta cohesion;
   - mortality vs next-window delta cohesion;
   - delta lineage concentration vs delta cohesion;
   - delta strategy dimensions vs delta action entropy.

2. **Partial correlations**
   - mortality/cohesion, lineage/cohesion and group-alignment/cohesion after linear control for tick and alive population.

3. **Cross-lag diagnostics**
   - mortality/cohesion correlations from -3 to +3 reporting windows;
   - positive lag means mortality leads cohesion.

4. **Trend slopes**
   - per-1000-tick slopes for population, founder lineages, largest-lineage share, strategy dimensions, action entropy, cohesion and affinity dimensions.

5. **Cross-seed sign consistency**
   - positive, negative and available run counts for raw, difference and partial statistics;
   - repeated direction is listed only when at least three runs have the same non-zero sign.

## Cultural-spread warning

If no committed or configured knowledge transfer is detected, the report marks knowledge cultural-spread metrics as non-interpretable. Private experience roots can remain extremely diverse even though no content crosses hosts; that is not evidence of cultural evolution.

## Compatibility

The command and output filenames remain unchanged:

```bash
python -m subject_evolution.long_run_analysis \
  run_a/evolution_progress.jsonl \
  run_b/evolution_progress.jsonl \
  --output analyses/combined
```

The machine schema is now `multi-seed-long-run-analysis-v2`. Raw v0.16 correlation keys remain available under `correlations_observational`.
