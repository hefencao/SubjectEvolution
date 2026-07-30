# v0.38 D1-C long-run and factorial plan

## Step 1: rerun the D1-B world under v0.38

The scientific configuration remains:

```text
configs/mvp_short_d1b_selective_harvest_longrun.json
```

Run:

```bash
se-multi \
  --config configs/mvp_short_d1b_selective_harvest_longrun.json \
  --seeds 10001,10002,10003 \
  --output runs/d1c_explicit_requests_multiseed \
  --backend gpu \
  --until-tick 1500
```

This rerun is required because v0.37 progress files did not record explicit
requested-channel amounts. Do not reconstruct those selective requests from
realized extraction.

## Step 2: analyze request composition

```bash
python -m se.analysis.long_run \
  runs/d1c_explicit_requests_multiseed/seed_10001/evolution_progress.jsonl \
  runs/d1c_explicit_requests_multiseed/seed_10002/evolution_progress.jsonl \
  runs/d1c_explicit_requests_multiseed/seed_10003/evolution_progress.jsonl \
  --output analyses/d1c_explicit_requests
```

Primary checks:

- requested share-composition dimensions and channel balance;
- realized share composition and extraction efficiency;
- resource-field dimensions;
- four capacity dimensions and utilization;
- population/action scale separated from composition.

## Step 3: execute paired factorial branches

```bash
se-d1-factorial \
  --run-dir runs/d1c_explicit_requests_multiseed/seed_10001 \
  --run-dir runs/d1c_explicit_requests_multiseed/seed_10002 \
  --run-dir runs/d1c_explicit_requests_multiseed/seed_10003 \
  --output analyses/d1c_factorial \
  --phases peak,trough \
  --horizon 120 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

## D2 entry gate

Proceed to D2 only if at least two seeds show:

1. non-trivial requested-channel composition dynamics;
2. non-trivial capacity use and retained capacity dimensions;
3. a repeated affinity or capacity expression effect on a downstream outcome;
4. an effect not explained only by total HARVEST scale or extraction efficiency;
5. no catastrophic population collapse caused by the measurement change.
