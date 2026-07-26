# Natural-event paired intervention matrix

Schema: `natural-event-paired-intervention-matrix-v1`
Plan SHA-256: `737312dd4659807a89323fd275e784b91166fbaa53cdf094b16ca24618091dbb`
Selection: `exposure-only-local-peak-selection-v1`

> Anchors are selected from exposure fields only; post-event outcome fields are excluded.

| Anchor | Seed | Event | Region | Tick | Checkpoint | z-score | Eligible interventions |
|---|---:|---|---:|---:|---:|---:|---|
| seed_10001-crowding-r14-t270 | 10001 | crowding | 14 | 270 | 240 | 3.812 | disable-knowledge-transfer, disable-knowledge-policy, ablate-working-memory, bypass-sparse-selection, freeze-group-refresh, neutralize-resource-affinity |
| seed_10001-crowding-r7-t300 | 10001 | crowding | 7 | 300 | 240 | 3.646 | disable-knowledge-transfer, disable-knowledge-policy, ablate-working-memory, bypass-sparse-selection, freeze-group-refresh, neutralize-resource-affinity |
| seed_10001-mortality-r7-t420 | 10001 | mortality | 7 | 420 | 360 | 3.335 | disable-knowledge-transfer, disable-knowledge-policy, ablate-working-memory, bypass-sparse-selection, freeze-group-refresh, neutralize-resource-affinity |
| seed_10001-mortality-r4-t510 | 10001 | mortality | 4 | 510 | 480 | 3.786 | disable-knowledge-transfer, disable-knowledge-policy, ablate-working-memory, bypass-sparse-selection, freeze-group-refresh, neutralize-resource-affinity |
| seed_10001-scarcity-r8-t1410 | 10001 | scarcity | 8 | 1410 | 1380 | 0.572 | disable-knowledge-transfer, disable-knowledge-policy, ablate-working-memory, bypass-sparse-selection, freeze-group-refresh, neutralize-resource-affinity |
| seed_10001-scarcity-r4-t1470 | 10001 | scarcity | 4 | 1470 | 1440 | 0.596 | disable-knowledge-transfer, disable-knowledge-policy, ablate-working-memory, bypass-sparse-selection, freeze-group-refresh, neutralize-resource-affinity |
| seed_10002-crowding-r12-t240 | 10002 | crowding | 12 | 240 | 180 | 3.903 | disable-knowledge-transfer, disable-knowledge-policy, ablate-working-memory, bypass-sparse-selection, freeze-group-refresh, neutralize-resource-affinity |
| seed_10002-crowding-r15-t330 | 10002 | crowding | 15 | 330 | 300 | 3.926 | disable-knowledge-transfer, disable-knowledge-policy, ablate-working-memory, bypass-sparse-selection, freeze-group-refresh, neutralize-resource-affinity |
| seed_10002-mortality-r11-t420 | 10002 | mortality | 11 | 420 | 360 | 3.563 | disable-knowledge-transfer, disable-knowledge-policy, ablate-working-memory, bypass-sparse-selection, freeze-group-refresh, neutralize-resource-affinity |
| seed_10002-mortality-r14-t570 | 10002 | mortality | 14 | 570 | 540 | 3.512 | disable-knowledge-transfer, disable-knowledge-policy, ablate-working-memory, bypass-sparse-selection, freeze-group-refresh, neutralize-resource-affinity |
| seed_10002-scarcity-r8-t450 | 10002 | scarcity | 8 | 450 | 420 | 0.563 | disable-knowledge-transfer, disable-knowledge-policy, ablate-working-memory, bypass-sparse-selection, freeze-group-refresh, neutralize-resource-affinity |
| seed_10002-scarcity-r13-t1320 | 10002 | scarcity | 13 | 1320 | 1260 | 0.574 | disable-knowledge-transfer, disable-knowledge-policy, ablate-working-memory, bypass-sparse-selection, freeze-group-refresh, neutralize-resource-affinity |
| seed_10003-crowding-r7-t270 | 10003 | crowding | 7 | 270 | 240 | 3.478 | disable-knowledge-transfer, disable-knowledge-policy, ablate-working-memory, bypass-sparse-selection, freeze-group-refresh, neutralize-resource-affinity |
| seed_10003-crowding-r2-t300 | 10003 | crowding | 2 | 300 | 240 | 3.462 | disable-knowledge-transfer, disable-knowledge-policy, ablate-working-memory, bypass-sparse-selection, freeze-group-refresh, neutralize-resource-affinity |
| seed_10003-mortality-r7-t390 | 10003 | mortality | 7 | 390 | 360 | 3.521 | disable-knowledge-transfer, disable-knowledge-policy, ablate-working-memory, bypass-sparse-selection, freeze-group-refresh, neutralize-resource-affinity |
| seed_10003-mortality-r2-t450 | 10003 | mortality | 2 | 450 | 420 | 3.827 | disable-knowledge-transfer, disable-knowledge-policy, ablate-working-memory, bypass-sparse-selection, freeze-group-refresh, neutralize-resource-affinity |
| seed_10003-scarcity-r13-t1080 | 10003 | scarcity | 13 | 1080 | 1020 | 0.578 | disable-knowledge-transfer, disable-knowledge-policy, ablate-working-memory, bypass-sparse-selection, freeze-group-refresh, neutralize-resource-affinity |
| seed_10003-scarcity-r14-t1290 | 10003 | scarcity | 14 | 1290 | 1260 | 0.549 | disable-knowledge-transfer, disable-knowledge-policy, ablate-working-memory, bypass-sparse-selection, freeze-group-refresh, neutralize-resource-affinity |

## Selection boundary

Anchor selection is exposure-blind with respect to recorded outcomes, but the events are naturally occurring rather than randomized. Paired checkpoint branches identify short-horizon mechanism effects conditional on the selected events; they do not prove that the event exposure itself caused the observed world trajectory.

Excluded outcome fields:

- `spatial_local_region_boundary_cohesion`
- `spatial_local_region_new_transferred_roots`
- `spatial_local_region_lost_transferred_roots`
- `spatial_local_region_active_transferred_roots`
- `spatial_local_region_incoming_transfer_commits`
- `spatial_local_region_outgoing_transfer_commits`
- `effective_lineages`
- `largest_lineage_fraction`
- `window_action_entropy`
