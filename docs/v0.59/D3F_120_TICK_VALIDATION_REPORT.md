# D3-F reduced 120-tick validation

Seeds: `59001`, `59002`; branches: original, reversed, neutral; observation period: 30 ticks.

All triplets shared the tick-0 checkpoint. Every response trajectory reached tick 120, resource movement occurred in every branch, active exposure was nonuniform, neutral support was exactly one, and both external ledgers closed in every branch.

| Seed | Branch | Mean support gain | Positive fraction | Mean gradient cosine |
|---:|---|---:|---:|---:|
| 59001 | original | -0.0004396039 | 0.3885 | -0.1675 |
| 59001 | reversed | -0.0001619766 | 0.4201 | -0.0909 |
| 59001 | neutral | -0.0004859059 | 0.3851 | -0.1802 |
| 59002 | original | -0.0007986539 | 0.3395 | -0.2868 |
| 59002 | reversed | -0.0000805097 | 0.4469 | -0.0704 |
| 59002 | neutral | -0.0007426690 | 0.3474 | -0.2704 |

The short panel does not show positive support-aligned resource movement. It validates the audit path and shows why the project should not infer migration from the D3-E endpoint differences.
