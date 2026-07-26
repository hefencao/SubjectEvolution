# Natural-event event-timed execution plan

Manifest SHA-256: `737312dd4659807a89323fd275e784b91166fbaa53cdf094b16ca24618091dbb`
Execution-plan SHA-256: `2bc053cb039b592cd74e2a6ea2fa9395a4a67e8dfb1e295af61b2493181ebbfa`

- Intervention timing: `anchor-event-tick-v1`
- Selected anchors: 18
- Shared prefixes: 18
- Post-event trajectories: 72

| Prefix | Source tick | Event tick | Anchors |
|---|---:|---:|---:|
| 083f2bef83c22fcc-event-00000570 | 540 | 570 | 1 |
| 1118598eda27d6db-event-00000240 | 180 | 240 | 1 |
| 3e4e348ba5af189b-event-00000420 | 360 | 420 | 1 |
| 5568d6737845756a-event-00001320 | 1260 | 1320 | 1 |
| 588cbb7f3214e3b6-event-00000270 | 240 | 270 | 1 |
| 588cbb7f3214e3b6-event-00000300 | 240 | 300 | 1 |
| 81e25fa8724aa14d-event-00001470 | 1440 | 1470 | 1 |
| 9100c59082823c90-event-00000510 | 480 | 510 | 1 |
| a6c847d4aaf0df44-event-00000420 | 360 | 420 | 1 |
| a876cec8e8d2704c-event-00000450 | 420 | 450 | 1 |
| ac1feb0b85785a44-event-00001290 | 1260 | 1290 | 1 |
| b536d9f2260c348e-event-00000330 | 300 | 330 | 1 |
| c38e1a04e2296b8e-event-00000270 | 240 | 270 | 1 |
| c38e1a04e2296b8e-event-00000300 | 240 | 300 | 1 |
| d3f2f0bb00fc1c7d-event-00000450 | 420 | 450 | 1 |
| d495cbfc6165193f-event-00001080 | 1020 | 1080 | 1 |
| e8dba08d19beadb5-event-00000390 | 360 | 390 | 1 |
| f4c003cc3c426307-event-00001410 | 1380 | 1410 | 1 |

## Pairing boundary

Each prefix is replayed once from the signed source checkpoint to the nominal event tick. Baseline and interventions then load the same event checkpoint; common-boundary and cohort snapshots are captured before the intervention.
