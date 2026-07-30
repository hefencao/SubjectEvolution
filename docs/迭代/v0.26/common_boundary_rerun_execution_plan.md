# Natural-event execution plan

Manifest SHA-256: `737312dd4659807a89323fd275e784b91166fbaa53cdf094b16ca24618091dbb`
Execution-plan SHA-256: `874fa0d15313f6c8f0bdcc91cfdc9283bf4636e3f3e58130ad55133851887229`

- Selected anchors: 6
- Naive branches: 12
- Shared trajectories: 8
- Deduplicated branches: 4 (33.3%)
- Common checkpoint boundary audit: True

| Trajectory | Checkpoint | Intervention | Until tick | Anchors |
|---|---:|---|---:|---:|
| 1118598eda27d6db-baseline | 180 | baseline | 360 | 1 |
| 1118598eda27d6db-freeze_group_refresh | 180 | freeze-group-refresh | 360 | 1 |
| 588cbb7f3214e3b6-baseline | 240 | baseline | 420 | 2 |
| 588cbb7f3214e3b6-freeze_group_refresh | 240 | freeze-group-refresh | 420 | 2 |
| b536d9f2260c348e-baseline | 300 | baseline | 450 | 1 |
| b536d9f2260c348e-freeze_group_refresh | 300 | freeze-group-refresh | 450 | 1 |
| c38e1a04e2296b8e-baseline | 240 | baseline | 420 | 2 |
| c38e1a04e2296b8e-freeze_group_refresh | 240 | freeze-group-refresh | 420 | 2 |

## Pairing boundary

Every intervention comparison uses the baseline trajectory from the same checkpoint hash. A longer shared trajectory may serve multiple anchors only when checkpoint and intervention are identical; region summaries are still computed separately at each anchor's event tick and horizon.
