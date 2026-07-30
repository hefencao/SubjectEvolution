# Natural-event event-timed execution plan

Manifest SHA-256: `737312dd4659807a89323fd275e784b91166fbaa53cdf094b16ca24618091dbb`
Execution-plan SHA-256: `f2839146808ab81467ecbc6c5ae69dacc788fafd5285588db518eac9de0301cc`

- Intervention timing: `anchor-event-tick-v1`
- Selected anchors: 12
- Shared prefixes: 12
- Post-event trajectories: 48

| Prefix | Source tick | Event tick | Anchors |
|---|---:|---:|---:|
| 083f2bef83c22fcc-event-00000570 | 540 | 570 | 1 |
| 3e4e348ba5af189b-event-00000420 | 360 | 420 | 1 |
| 5568d6737845756a-event-00001320 | 1260 | 1320 | 1 |
| 81e25fa8724aa14d-event-00001470 | 1440 | 1470 | 1 |
| 9100c59082823c90-event-00000510 | 480 | 510 | 1 |
| a6c847d4aaf0df44-event-00000420 | 360 | 420 | 1 |
| a876cec8e8d2704c-event-00000450 | 420 | 450 | 1 |
| ac1feb0b85785a44-event-00001290 | 1260 | 1290 | 1 |
| d3f2f0bb00fc1c7d-event-00000450 | 420 | 450 | 1 |
| d495cbfc6165193f-event-00001080 | 1020 | 1080 | 1 |
| e8dba08d19beadb5-event-00000390 | 360 | 390 | 1 |
| f4c003cc3c426307-event-00001410 | 1380 | 1410 | 1 |

## Pairing boundary

Each prefix is replayed once from the signed source checkpoint to the nominal event tick. Baseline and interventions then load the same event checkpoint; common-boundary and cohort snapshots are captured before the intervention.
