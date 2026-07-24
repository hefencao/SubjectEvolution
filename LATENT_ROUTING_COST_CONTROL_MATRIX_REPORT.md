# Latent Routing Cost Control Matrix — v0.12.0

## Common setup

- backend: CPU reference
- seed: 10001
- ticks: 30
- initial/max entities: 500 / 768
- latent levels: 4, 8, 16, 32
- duplicate runs: two per primary condition
- checkpoints: ticks 15 and 30

The matrix is intentionally short. It validates mechanics, reproducibility and budget matching; it does not claim long-term adaptation.

## Cost coefficients

Same-unit L1/L2 conditions use:

```text
per latent dimension: 2.0e-8
per MAC:              4.0e-8
per active hidden:    1.0e-8
per emitted action:   2.0e-6
per saturation:       1.0e-7
per clipped output:   1.0e-7
base invocation:      0
```

The budget-matched L2 condition changes only the MAC unit to `2.865e-8`.

## Results

| Condition | Alive | Births | Mean energy | Routing energy | MAC count | Policy action changes |
|---|---:|---:|---:|---:|---:|---:|
| L1 no-cost | 604 | 104 | 1.99502 | 0 | 0 | 2,654 |
| L1 costed | 604 | 104 | 1.99360 | 0.861617 | 15,261,376 | 2,653 |
| L2 no-cost | 605 | 105 | 1.96438 | 0 | 0 | 2,545 |
| L2 same-unit costed | 604 | 104 | 1.96719 | 1.100320 | 21,029,896 | 2,541 |
| L2 budget-matched | 604 | 104 | 1.96758 | 0.861541 | 21,027,504 | 2,540 |

The L1/L2 matched budget gap is `0.00007585`, or about `0.0088%` of the L1 charge.

No ordinary matrix condition rejected a route request. Therefore its direct cost-induced action-change count is zero: cost affects subsequent physical state rather than removing a current residual.

## Rejection stress test

A separate 10-tick, 64-entity L2 scenario used a base routing request of 2.0 energy:

| Measure | Value |
|---|---:|
| requested entity-routes | 488 |
| committed entity-routes | 37 |
| rejected entity-routes | 451 |
| rejected action residual cells | 3,606 |
| cost-induced sampled action changes | 68 |
| requested energy | 976 |
| committed energy | 74 |

This confirms that budget rejection changes actual action selection when knowledge residuals cannot be paid.

## Reproducibility

For each of the five main conditions, the duplicate pair matched on:

- 204 non-timing metrics fields;
- knowledge events;
- outcome updates;
- policy contribution logs;
- transfer logs;
- routing cost logs where enabled;
- evolution progress logs;
- all 35 checkpoint arrays at ticks 15 and 30.

## Interpretation limits

- L2 uses more counted MACs than L1 under the same observed knowledge workload.
- Equal energy budget does not mean equal representational capacity or equal action effect.
- One seed and 30 ticks cannot establish evolutionary advantage.
- The cost coefficients are model parameters and require future sweeps.
