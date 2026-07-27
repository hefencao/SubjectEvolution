# v0.39 workflow and persistent release environment

## Why `release-check` did not expose `se-d1-factorial`

`release-check` creates a temporary directory and venv, validates the candidate,
then deletes that directory. A child process also cannot modify the parent zsh's
`PATH`. Passing artifact validation therefore never implied that the current
shell had installed the candidate.

## Persistent verified environment

```bash
make release-env \
  PREVIOUS_WHEEL=/mnt/c/Users/hefen/Downloads/se_mvp-0.38.0-py3-none-any.whl
source .release-env/venv/bin/activate
```

Without activation:

```bash
.release-env/venv/bin/se --help
.release-env/venv/bin/se-d1-factorial --help
```

The target recreates `.release-env`, so stale package files do not accumulate.
It force-reinstalls the candidate over the supplied prior wheel and verifies
that `se.__file__` belongs to the persistent venv's `site-packages`.

## Exact checkpoints

Single run:

```bash
se \
  --config configs/mvp_short_d1b_selective_harvest_longrun.json \
  --seed 10001 \
  --checkpoint-ticks 2400,2640 \
  --until-tick 3000 \
  --output runs/d1c_seed_10001 \
  --backend gpu
```

Sequential multi-seed run:

```bash
se-multi \
  --config configs/mvp_short_d1b_selective_harvest_longrun.json \
  --seeds 10001,10002,10003 \
  --checkpoint-ticks 2400,2640,2760,2820,2880,3000 \
  --until-tick 3000 \
  --output runs/d1c_multiseed \
  --backend gpu
```

Every seed receives the same exact-tick union. This intentionally avoids three
almost-identical configs. Checkpoints after a resumed checkpoint can also be
scheduled with the same option.

## Reusing a factorial plan

```bash
se-d1-factorial \
  --plan d1_factorial_plan.json \
  --output analyses/d1_factorial_repeat \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

This executes the checkpoint paths and horizons already recorded in the plan;
it does not require the source trajectory to be rescanned for another complete
population cycle.

## Cycle terminology

The phase planner detects an observed `trough→peak→trough` **population cycle**.
The old error called this an “ecological cycle”, which was too broad. v0.39 uses
the more precise wording. `--allow-incomplete-cycle` remains smoke-only.
## Short multi-seed smoke runs

A run that ends before the first evolution-evaluation window is still a valid
world smoke test. `se-multi` now records that seed as `completed-no-progress`
and writes `multi-seed-analysis-unavailable-v1` instead of failing because
`evolution_progress.jsonl` does not yet exist.

