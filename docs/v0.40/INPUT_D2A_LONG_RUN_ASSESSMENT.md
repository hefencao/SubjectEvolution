# Input D2-A 3000-tick long-run assessment

Source schema: `multi-seed-long-run-analysis-v14`; analyzer/runtime: `0.39.0` / `['0.39.0']`.

| Run | Alive | Effective lineages | Largest lineage | Strategy dims | Env dims | Capacity dims | Expressed modules | Residual | Changed entities | Residual trend/1000 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| seed_10001 | 476 | 2.063 | 0.639 | 1.909 | 2.125 | 2.989 | 2.562 | 0.000188 | 0.998 | -0.000034 |
| seed_10002 | 582 | 1.715 | 0.746 | 2.074 | 1.936 | 2.919 | 2.637 | 0.000136 | 0.926 | -0.000056 |
| seed_10003 | 456 | 3.478 | 0.496 | 4.020 | 1.850 | 2.765 | 2.762 | 0.000485 | 0.998 | +0.000048 |

## Supported observations

- The environment remains non-trivially multidimensional (`1.85–2.12`) and capacities remain multidimensional (`2.76–2.99`).
- `2.56–2.76` of four modules are expressed on average and `92.6–99.8%` of entities receive a non-zero final preference change.
- The final mean absolute module residual is only `0.000136–0.000485`.
- Residual magnitude declines in seeds 10001 and 10002; functional harvest-preference dimensionality declines in every seed.
- Effective lineage count falls to `1.72–3.48`; the largest lineage occupies `49.6–74.6%` of survivors. Strategy dimensions also collapse to `1.91–4.02`.
- Requested-share dimensionality remains non-trivial (`1.89–2.82`), but that does not identify which module caused it.

## Decision

**Do not add module duplication, deletion, arbitrary rerouting, or new physical ports in this version.**

Proceed to D2-B: measure isolated module contribution and execute shared-checkpoint all-module and leave-one-module-out neutralization. This distinguishes structural expression from actual causal function, redundancy, cancellation, and historical fixation.

## Interpretation boundary

These runs are observational. Declining diversity could reflect selection, drift, founder effects, or the current world architecture. D2-B can identify local expression effects but still cannot establish universal module necessity or open-ended novelty.
