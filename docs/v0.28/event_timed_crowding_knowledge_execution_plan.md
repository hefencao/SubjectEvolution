# Natural-event event-timed execution plan

Manifest SHA-256: `737312dd4659807a89323fd275e784b91166fbaa53cdf094b16ca24618091dbb`
Execution-plan SHA-256: `27ec8e8216b481c7e7a0305ba6eabb989bc831b4417a436a2a685fb83ba43bca`

- Intervention timing: `anchor-event-tick-v1`
- Selected anchors: 6
- Shared prefixes: 6
- Post-event trajectories: 24

| Prefix | Source tick | Event tick | Anchors |
|---|---:|---:|---:|
| 1118598eda27d6db-event-00000240 | 180 | 240 | 1 |
| 588cbb7f3214e3b6-event-00000270 | 240 | 270 | 1 |
| 588cbb7f3214e3b6-event-00000300 | 240 | 300 | 1 |
| b536d9f2260c348e-event-00000330 | 300 | 330 | 1 |
| c38e1a04e2296b8e-event-00000270 | 240 | 270 | 1 |
| c38e1a04e2296b8e-event-00000300 | 240 | 300 | 1 |

## Pairing boundary

Each prefix is replayed once from the signed source checkpoint to the nominal event tick. Baseline and interventions then load the same event checkpoint; common-boundary and cohort snapshots are captured before the intervention.
