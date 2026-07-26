# Structural measurement protocol audit

Schema: `structural-measurement-protocol-audit-v1`
Audit SHA-256: `628bf5829e93023888f4cd092c4c3060495fe1c13f3e3aabb1ecb7ef67589355`

## Group label

- schema: `trusted-directed-fixed-round-min-label-v1`
- threshold / rounds / minimum members: 0.12 / 8 / 6
- refresh mode: `adaptive-topology-v1`
- propagation: initialize label as physical slot index; for each fixed round, replace an entity label by the minimum of its current label and labels reachable through eligible outgoing relation slots
- token: stable entity ID at the propagated minimum root slot; components below minimum members receive token 0 and remain ungrouped
- boundary: finite-round directed minimum-label propagation is an approximate candidate-group measurement, not a subject-existence verdict

## Spatial regions

- schema: `normalized-fixed-count-grid-v1`
- grid: 4 × 4 (16 regions)
- physical region: 32.0 × 32.0
- world cells per region: 8.0 × 8.0
- grid-aligned: True
- map-size semantics: fixed region counts over normalized coordinates; physical area and represented world-cell count scale with map dimensions and resolution

## Anchor selection

- schema: `exposure-only-local-peak-selection-v1`
- event kinds: scarcity, crowding, mortality
- quantile / maximum per kind per run / gap windows: 0.8 / 2 / 2
- candidate rule: per-region within-run quantile threshold; interior local maximum; minimum gap enforced independently within each region
- ranking: descending within-region z-score, then earlier tick, then lower region ID
- region diversity: prefer distinct regions until max_events; reuse a region only after all candidate-bearing regions are represented
- checkpoint: choose the latest full checkpoint with checkpoint_tick < event_tick
- boundary: anchors are high local exposure peaks conditional on observed natural events; they are not randomized exposure assignments
