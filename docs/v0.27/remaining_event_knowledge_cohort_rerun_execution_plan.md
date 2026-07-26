# Natural-event execution plan

Manifest SHA-256: `737312dd4659807a89323fd275e784b91166fbaa53cdf094b16ca24618091dbb`
Execution-plan SHA-256: `4084551bb80a92849b340863e55cd0e1ce10a9c7479fc6284c9d45d1ef19cd26`

- Selected anchors: 12
- Naive branches: 48
- Shared trajectories: 48
- Deduplicated branches: 0 (0.0%)
- Common checkpoint boundary audit: True
- Event cohort endpoint audit: True

| Trajectory | Checkpoint | Intervention | Until tick | Anchors |
|---|---:|---|---:|---:|
| 083f2bef83c22fcc-ablate_working_memory | 540 | ablate-working-memory | 690 | 1 |
| 083f2bef83c22fcc-baseline | 540 | baseline | 690 | 1 |
| 083f2bef83c22fcc-bypass_sparse_selection | 540 | bypass-sparse-selection | 690 | 1 |
| 083f2bef83c22fcc-disable_knowledge_policy | 540 | disable-knowledge-policy | 690 | 1 |
| 3e4e348ba5af189b-ablate_working_memory | 360 | ablate-working-memory | 540 | 1 |
| 3e4e348ba5af189b-baseline | 360 | baseline | 540 | 1 |
| 3e4e348ba5af189b-bypass_sparse_selection | 360 | bypass-sparse-selection | 540 | 1 |
| 3e4e348ba5af189b-disable_knowledge_policy | 360 | disable-knowledge-policy | 540 | 1 |
| 5568d6737845756a-ablate_working_memory | 1260 | ablate-working-memory | 1440 | 1 |
| 5568d6737845756a-baseline | 1260 | baseline | 1440 | 1 |
| 5568d6737845756a-bypass_sparse_selection | 1260 | bypass-sparse-selection | 1440 | 1 |
| 5568d6737845756a-disable_knowledge_policy | 1260 | disable-knowledge-policy | 1440 | 1 |
| 81e25fa8724aa14d-ablate_working_memory | 1440 | ablate-working-memory | 1590 | 1 |
| 81e25fa8724aa14d-baseline | 1440 | baseline | 1590 | 1 |
| 81e25fa8724aa14d-bypass_sparse_selection | 1440 | bypass-sparse-selection | 1590 | 1 |
| 81e25fa8724aa14d-disable_knowledge_policy | 1440 | disable-knowledge-policy | 1590 | 1 |
| 9100c59082823c90-ablate_working_memory | 480 | ablate-working-memory | 630 | 1 |
| 9100c59082823c90-baseline | 480 | baseline | 630 | 1 |
| 9100c59082823c90-bypass_sparse_selection | 480 | bypass-sparse-selection | 630 | 1 |
| 9100c59082823c90-disable_knowledge_policy | 480 | disable-knowledge-policy | 630 | 1 |
| a6c847d4aaf0df44-ablate_working_memory | 360 | ablate-working-memory | 540 | 1 |
| a6c847d4aaf0df44-baseline | 360 | baseline | 540 | 1 |
| a6c847d4aaf0df44-bypass_sparse_selection | 360 | bypass-sparse-selection | 540 | 1 |
| a6c847d4aaf0df44-disable_knowledge_policy | 360 | disable-knowledge-policy | 540 | 1 |
| a876cec8e8d2704c-ablate_working_memory | 420 | ablate-working-memory | 570 | 1 |
| a876cec8e8d2704c-baseline | 420 | baseline | 570 | 1 |
| a876cec8e8d2704c-bypass_sparse_selection | 420 | bypass-sparse-selection | 570 | 1 |
| a876cec8e8d2704c-disable_knowledge_policy | 420 | disable-knowledge-policy | 570 | 1 |
| ac1feb0b85785a44-ablate_working_memory | 1260 | ablate-working-memory | 1410 | 1 |
| ac1feb0b85785a44-baseline | 1260 | baseline | 1410 | 1 |
| ac1feb0b85785a44-bypass_sparse_selection | 1260 | bypass-sparse-selection | 1410 | 1 |
| ac1feb0b85785a44-disable_knowledge_policy | 1260 | disable-knowledge-policy | 1410 | 1 |
| d3f2f0bb00fc1c7d-ablate_working_memory | 420 | ablate-working-memory | 570 | 1 |
| d3f2f0bb00fc1c7d-baseline | 420 | baseline | 570 | 1 |
| d3f2f0bb00fc1c7d-bypass_sparse_selection | 420 | bypass-sparse-selection | 570 | 1 |
| d3f2f0bb00fc1c7d-disable_knowledge_policy | 420 | disable-knowledge-policy | 570 | 1 |
| d495cbfc6165193f-ablate_working_memory | 1020 | ablate-working-memory | 1200 | 1 |
| d495cbfc6165193f-baseline | 1020 | baseline | 1200 | 1 |
| d495cbfc6165193f-bypass_sparse_selection | 1020 | bypass-sparse-selection | 1200 | 1 |
| d495cbfc6165193f-disable_knowledge_policy | 1020 | disable-knowledge-policy | 1200 | 1 |
| e8dba08d19beadb5-ablate_working_memory | 360 | ablate-working-memory | 510 | 1 |
| e8dba08d19beadb5-baseline | 360 | baseline | 510 | 1 |
| e8dba08d19beadb5-bypass_sparse_selection | 360 | bypass-sparse-selection | 510 | 1 |
| e8dba08d19beadb5-disable_knowledge_policy | 360 | disable-knowledge-policy | 510 | 1 |
| f4c003cc3c426307-ablate_working_memory | 1380 | ablate-working-memory | 1530 | 1 |
| f4c003cc3c426307-baseline | 1380 | baseline | 1530 | 1 |
| f4c003cc3c426307-bypass_sparse_selection | 1380 | bypass-sparse-selection | 1530 | 1 |
| f4c003cc3c426307-disable_knowledge_policy | 1380 | disable-knowledge-policy | 1530 | 1 |

## Pairing boundary

Every intervention comparison uses the baseline trajectory from the same checkpoint hash. A longer shared trajectory may serve multiple anchors only when checkpoint and intervention are identical; region summaries are still computed separately at each anchor's event tick and horizon.
