# Structural measurement protocol audit

Schema: `structural-measurement-protocol-audit-v3`
Audit SHA-256: `adf49a12dfdbd27ccf7513bbb403a8c0f7eba774b57b3bfa5505d8e1a558ba6e`

## Group label

- schema: `trusted-directed-fixed-round-min-label-v1`
- threshold / rounds / minimum members: 0.12 / 8 / 6
- refresh mode: `adaptive-topology-v1`
- propagation: initialize label as physical slot index; for each fixed round, replace an entity label by the minimum of its current label and labels reachable through eligible outgoing relation slots
- token: stable entity ID at the propagated minimum root slot; components below minimum members receive token 0 and remain ungrouped
- boundary: finite-round directed minimum-label propagation is an approximate candidate-group measurement, not a subject-existence verdict

## Subject succession

- enabled / schema: True / `stable-membership-subject-succession-v1`
- identity key: stable entity ID membership
- transition rule: connect previous and current candidate groups when they share at least one stable entity ID; classify zero/one/multiple overlap relations as formation, persistence, split, merge, or dissolution
- boundary: membership succession among candidate social structures; not an ontological identity theorem, arbitrary nesting graph, or subjecthood score

## Spatial regions

- schema: `normalized-fixed-count-grid-v1`
- grid: 4 × 4 (16 regions)
- physical region: 32.0 × 32.0
- world cells per region: 8.0 × 8.0
- grid-aligned: True
- map-size semantics: fixed region counts over normalized coordinates; physical area and represented world-cell count scale with map dimensions and resolution

## Resource environment

- schema / channels: `orthogonal-four-resource-niche-v1` / 4
- independent cycle periods: [173, 257, 349, 431]
- primary wave vectors: [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, -1.0]]
- diffusion rates: [0.002, 0.004, 0.006, 0.008]
- entity/lineage/group aware: False / False / False
- boundary: fixed four-channel physical interface with independently configured spatial, temporal, and diffusion dynamics; configuration can create environmental axes but does not guarantee evolved ecological differentiation

## Environment atlas

- enabled / schema: True / `multiscale-subject-environment-atlas-v2`
- scales: 2×2, 4×4, 8×8
- signature: four capacity-normalized resource means, hazard mean, mortality-trace mean
- resource-only metrics: resource effective dimensions, resource channel correlation matrix, mean/max absolute resource channel correlation
- subject exposure: between-label share of realized regional signature variance for genetic lineages and observed social groups
- boundary: descriptive multiscale environment heterogeneity and exposure segregation; not environmental causation or subjecthood
