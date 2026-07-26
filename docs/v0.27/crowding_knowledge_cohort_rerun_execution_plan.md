# Natural-event execution plan

Manifest SHA-256: `737312dd4659807a89323fd275e784b91166fbaa53cdf094b16ca24618091dbb`
Execution-plan SHA-256: `fda5602b76b9b63ff9bea750df1fcb1bf477590da16d957fb807d62686c081bc`

- Selected anchors: 6
- Naive branches: 24
- Shared trajectories: 16
- Deduplicated branches: 8 (33.3%)
- Common checkpoint boundary audit: True
- Event cohort endpoint audit: True

| Trajectory | Checkpoint | Intervention | Until tick | Anchors |
|---|---:|---|---:|---:|
| 1118598eda27d6db-ablate_working_memory | 180 | ablate-working-memory | 360 | 1 |
| 1118598eda27d6db-baseline | 180 | baseline | 360 | 1 |
| 1118598eda27d6db-bypass_sparse_selection | 180 | bypass-sparse-selection | 360 | 1 |
| 1118598eda27d6db-disable_knowledge_policy | 180 | disable-knowledge-policy | 360 | 1 |
| 588cbb7f3214e3b6-ablate_working_memory | 240 | ablate-working-memory | 420 | 2 |
| 588cbb7f3214e3b6-baseline | 240 | baseline | 420 | 2 |
| 588cbb7f3214e3b6-bypass_sparse_selection | 240 | bypass-sparse-selection | 420 | 2 |
| 588cbb7f3214e3b6-disable_knowledge_policy | 240 | disable-knowledge-policy | 420 | 2 |
| b536d9f2260c348e-ablate_working_memory | 300 | ablate-working-memory | 450 | 1 |
| b536d9f2260c348e-baseline | 300 | baseline | 450 | 1 |
| b536d9f2260c348e-bypass_sparse_selection | 300 | bypass-sparse-selection | 450 | 1 |
| b536d9f2260c348e-disable_knowledge_policy | 300 | disable-knowledge-policy | 450 | 1 |
| c38e1a04e2296b8e-ablate_working_memory | 240 | ablate-working-memory | 420 | 2 |
| c38e1a04e2296b8e-baseline | 240 | baseline | 420 | 2 |
| c38e1a04e2296b8e-bypass_sparse_selection | 240 | bypass-sparse-selection | 420 | 2 |
| c38e1a04e2296b8e-disable_knowledge_policy | 240 | disable-knowledge-policy | 420 | 2 |

## Pairing boundary

Every intervention comparison uses the baseline trajectory from the same checkpoint hash. A longer shared trajectory may serve multiple anchors only when checkpoint and intervention are identical; region summaries are still computed separately at each anchor's event tick and horizon.
