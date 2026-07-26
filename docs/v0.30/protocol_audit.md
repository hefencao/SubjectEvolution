# Structural measurement protocol audit

Schema: `structural-measurement-protocol-audit-v2`
Audit SHA-256: `34f8820e82a2014e735319993695b1fa8bb47a94d66957592a9e87aaa129eb6c`

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

## Environment atlas

- enabled / schema: True / `multiscale-subject-environment-atlas-v1`
- scales: 2×2, 4×4, 8×8
- signature: four capacity-normalized resource means, hazard mean, mortality-trace mean
- subject exposure: between-label share of realized regional signature variance for genetic lineages and observed social groups
- boundary: descriptive multiscale environment heterogeneity and exposure segregation; not environmental causation or subjecthood
