# Structural measurement protocol audit

Schema: `structural-measurement-protocol-audit-v4`
Audit SHA-256: `4175a9fe0585b9c17e79373d88d08c4c4d13d2b964409be7f4d66fd7cc422b00`

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

## Elastic capacities

- enabled / schema: True / `inherited-elastic-capacities-v1`
- physical maxima: {'working_memory_dimensions': 4, 'knowledge_bytes': 512, 'relation_slots': 8, 'knowledge_attention_slots': 2}
- effective bounds: {'working_memory_dimensions': [0, 4], 'knowledge_bytes': [0, 512], 'relation_slots': [0, 8], 'knowledge_attention_slots': [0, 2]}
- gene start/count: 535 / 4
- mutation probability/std: 0.03 / 0.16
- maintenance energy: {'per_working_memory_dimension': 1e-05, 'per_knowledge_byte': 1e-07, 'per_relation_slot': 5e-06, 'per_attention_slot': 1e-05}
- development energy: {'per_working_memory_dimension': 0.002, 'per_knowledge_byte': 1e-05, 'per_relation_slot': 0.001, 'per_attention_slot': 0.002}
- preset roles / diversity protection: False / False
- boundary: four inherited capacities alter the usable scale and explicit cost of existing memory, knowledge, relationship, and attention mechanisms; they do not add a predefined ecological role or guarantee adaptive differentiation

## Environment atlas

- enabled / schema: True / `multiscale-subject-environment-atlas-v2`
- scales: 2×2, 4×4, 8×8
- signature: four capacity-normalized resource means, hazard mean, mortality-trace mean
- resource-only metrics: resource effective dimensions, resource channel correlation matrix, mean/max absolute resource channel correlation
- subject exposure: between-label share of realized regional signature variance for genetic lineages and observed social groups
- boundary: descriptive multiscale environment heterogeneity and exposure segregation; not environmental causation or subjecthood
