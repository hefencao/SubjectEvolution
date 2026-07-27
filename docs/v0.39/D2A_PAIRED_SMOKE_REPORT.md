# D2-A 300-tick paired smoke

## Design

- seed: 10001;
- CPU reference;
- 200 initial entities, capacity 512;
- D0 + D1-A + D1-B;
- identical initial genotype prefix, IDs and keyed random streams;
- baseline: D2-A expressed from tick 0;
- paired branch: `neutralize-functional-modules` from tick 0;
- total harvest request budget unchanged.

The neutralized D2 configuration reproduces the D1-B endpoint, confirming that
appended module genes and the disabled output path do not alter the existing
world trajectory.

## Endpoint

| Metric | Module expressed | Module neutral | Effect |
|---|---:|---:|---:|
| Alive | 127 | 115 | +12 |
| Environment resource dimensions | 1.7133 | 1.8248 | -0.1115 |
| Extraction efficiency | 0.8156 | 0.8713 | -0.0557 |
| Effective transferred roots | 20.1667 | 17.0000 | +3.1667 |
| Capacity dimensions | 3.8599 | 3.8532 | +0.0067 |
| Changed-request entity fraction | 0.8268 | 0 | +0.8268 |
| Mean absolute module residual share | 0.000280 | 0 | +0.000280 |

Final expressed modules per entity average `1.764`, and mean gate strength is
`0.0848`. The observed residual is small but reaches 82.7% of entities because
exclusive channel sampling can respond to small probability shifts over many
attempts.

## Later intervention check

Neutralizing only from tick 150 to 300 changes the endpoint relative to the
continuous baseline by:

- alive: `127→124`;
- environment dimensions: `1.7133→1.7321`;
- extraction efficiency: `0.8156→0.8320`;
- transferred roots: `20.17→21.00`.

The direction differs by outcome and horizon. This confirms causal participation
but not uniform benefit.

## Decision

D2-A is retained as an exploratory mainline mechanism because it produces a
bounded, paid and ablatable contextual effect. It does not yet pass the gate for
module duplication, arbitrary output routing or new physical functions.
