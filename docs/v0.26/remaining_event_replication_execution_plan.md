# Natural-event execution plan

Manifest SHA-256: `737312dd4659807a89323fd275e784b91166fbaa53cdf094b16ca24618091dbb`
Execution-plan SHA-256: `77f7bcc8bcabc75950d7d46f72d421a0bb42a0c93a3a88e8f50ec58bf466e246`

- Selected anchors: 12
- Naive branches: 48
- Shared trajectories: 48
- Deduplicated branches: 0 (0.0%)
- Common checkpoint boundary audit: True

| Trajectory | Checkpoint | Intervention | Until tick | Anchors |
|---|---:|---|---:|---:|
| 083f2bef83c22fcc-baseline | 540 | baseline | 690 | 1 |
| 083f2bef83c22fcc-disable_knowledge_transfer | 540 | disable-knowledge-transfer | 690 | 1 |
| 083f2bef83c22fcc-freeze_group_refresh | 540 | freeze-group-refresh | 690 | 1 |
| 083f2bef83c22fcc-neutralize_resource_affinity | 540 | neutralize-resource-affinity | 690 | 1 |
| 3e4e348ba5af189b-baseline | 360 | baseline | 540 | 1 |
| 3e4e348ba5af189b-disable_knowledge_transfer | 360 | disable-knowledge-transfer | 540 | 1 |
| 3e4e348ba5af189b-freeze_group_refresh | 360 | freeze-group-refresh | 540 | 1 |
| 3e4e348ba5af189b-neutralize_resource_affinity | 360 | neutralize-resource-affinity | 540 | 1 |
| 5568d6737845756a-baseline | 1260 | baseline | 1440 | 1 |
| 5568d6737845756a-disable_knowledge_transfer | 1260 | disable-knowledge-transfer | 1440 | 1 |
| 5568d6737845756a-freeze_group_refresh | 1260 | freeze-group-refresh | 1440 | 1 |
| 5568d6737845756a-neutralize_resource_affinity | 1260 | neutralize-resource-affinity | 1440 | 1 |
| 81e25fa8724aa14d-baseline | 1440 | baseline | 1590 | 1 |
| 81e25fa8724aa14d-disable_knowledge_transfer | 1440 | disable-knowledge-transfer | 1590 | 1 |
| 81e25fa8724aa14d-freeze_group_refresh | 1440 | freeze-group-refresh | 1590 | 1 |
| 81e25fa8724aa14d-neutralize_resource_affinity | 1440 | neutralize-resource-affinity | 1590 | 1 |
| 9100c59082823c90-baseline | 480 | baseline | 630 | 1 |
| 9100c59082823c90-disable_knowledge_transfer | 480 | disable-knowledge-transfer | 630 | 1 |
| 9100c59082823c90-freeze_group_refresh | 480 | freeze-group-refresh | 630 | 1 |
| 9100c59082823c90-neutralize_resource_affinity | 480 | neutralize-resource-affinity | 630 | 1 |
| a6c847d4aaf0df44-baseline | 360 | baseline | 540 | 1 |
| a6c847d4aaf0df44-disable_knowledge_transfer | 360 | disable-knowledge-transfer | 540 | 1 |
| a6c847d4aaf0df44-freeze_group_refresh | 360 | freeze-group-refresh | 540 | 1 |
| a6c847d4aaf0df44-neutralize_resource_affinity | 360 | neutralize-resource-affinity | 540 | 1 |
| a876cec8e8d2704c-baseline | 420 | baseline | 570 | 1 |
| a876cec8e8d2704c-disable_knowledge_transfer | 420 | disable-knowledge-transfer | 570 | 1 |
| a876cec8e8d2704c-freeze_group_refresh | 420 | freeze-group-refresh | 570 | 1 |
| a876cec8e8d2704c-neutralize_resource_affinity | 420 | neutralize-resource-affinity | 570 | 1 |
| ac1feb0b85785a44-baseline | 1260 | baseline | 1410 | 1 |
| ac1feb0b85785a44-disable_knowledge_transfer | 1260 | disable-knowledge-transfer | 1410 | 1 |
| ac1feb0b85785a44-freeze_group_refresh | 1260 | freeze-group-refresh | 1410 | 1 |
| ac1feb0b85785a44-neutralize_resource_affinity | 1260 | neutralize-resource-affinity | 1410 | 1 |
| d3f2f0bb00fc1c7d-baseline | 420 | baseline | 570 | 1 |
| d3f2f0bb00fc1c7d-disable_knowledge_transfer | 420 | disable-knowledge-transfer | 570 | 1 |
| d3f2f0bb00fc1c7d-freeze_group_refresh | 420 | freeze-group-refresh | 570 | 1 |
| d3f2f0bb00fc1c7d-neutralize_resource_affinity | 420 | neutralize-resource-affinity | 570 | 1 |
| d495cbfc6165193f-baseline | 1020 | baseline | 1200 | 1 |
| d495cbfc6165193f-disable_knowledge_transfer | 1020 | disable-knowledge-transfer | 1200 | 1 |
| d495cbfc6165193f-freeze_group_refresh | 1020 | freeze-group-refresh | 1200 | 1 |
| d495cbfc6165193f-neutralize_resource_affinity | 1020 | neutralize-resource-affinity | 1200 | 1 |
| e8dba08d19beadb5-baseline | 360 | baseline | 510 | 1 |
| e8dba08d19beadb5-disable_knowledge_transfer | 360 | disable-knowledge-transfer | 510 | 1 |
| e8dba08d19beadb5-freeze_group_refresh | 360 | freeze-group-refresh | 510 | 1 |
| e8dba08d19beadb5-neutralize_resource_affinity | 360 | neutralize-resource-affinity | 510 | 1 |
| f4c003cc3c426307-baseline | 1380 | baseline | 1530 | 1 |
| f4c003cc3c426307-disable_knowledge_transfer | 1380 | disable-knowledge-transfer | 1530 | 1 |
| f4c003cc3c426307-freeze_group_refresh | 1380 | freeze-group-refresh | 1530 | 1 |
| f4c003cc3c426307-neutralize_resource_affinity | 1380 | neutralize-resource-affinity | 1530 | 1 |

## Pairing boundary

Every intervention comparison uses the baseline trajectory from the same checkpoint hash. A longer shared trajectory may serve multiple anchors only when checkpoint and intervention are identical; region summaries are still computed separately at each anchor's event tick and horizon.
