# Multi-seed Long-run Runner and Analyzer

## Run several seeds

```bash
python -m subject_evolution.multi_seed \
  --config configs/mvp_short_latent_l2_memory_topk_inherited_heterogeneous_budget_matched_longrun.json \
  --seeds 10001,10002,10003 \
  --output runs/heterogeneous_multiseed \
  --backend cpu \
  --until-tick 1500
```

The runner executes seeds sequentially and writes `multi_seed_index.json` after
each completed seed.  Re-running the same command skips completed seed
directories.  An incomplete directory is never overwritten silently; use
`--overwrite-partial` to restart it explicitly.

At completion it creates:

```text
long_run_analysis.json
long_run_analysis.md
```

## Analyze existing reports

```bash
python -m subject_evolution.long_run_analysis \
  runs/seed_10001/evolution_progress.jsonl \
  runs/seed_10002/evolution_progress.jsonl \
  --output analysis/two_seed
```

The analyzer accepts GUI-exported JSONL as long as each line is an evolution
progress record.

## Reported comparisons

- final population and lineage concentration;
- strategy effective dimensions and action entropy;
- boundary cohesion;
- lineage/group alignment when v0.16 fields are available;
- knowledge root diversity when available;
- within-run descriptive correlations, requiring at least five windows.

Every correlation is labelled observational.  The analyzer does not infer
intent, group agency or causal direction.
