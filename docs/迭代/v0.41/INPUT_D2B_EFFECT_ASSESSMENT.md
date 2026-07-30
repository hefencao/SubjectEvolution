# D2 module effect assessment

Schema: `d2-module-effect-assessment-v1`
Short / long horizon: `120` / `300` ticks
Checkpoint conditions: **6**

## Decision standard

1. Exact non-zero values only establish deterministic branch divergence.
2. Practical thresholds identify effects large enough to interpret.
3. A repeated effect requires the same material direction in at least four checkpoint conditions and at least two seeds, or a phase-specific direction in at least two seeds.
4. Direct footprint requires a material immediate change at the fixed harvest interface.
5. Module duplication additionally requires cross-lineage footprint, positive ecological persistence in at least two seeds, and no dominant-lineage guard failure.

### Practical effect thresholds

| Outcome | Role | Absolute threshold | Relative threshold |
|---|---|---:|---:|
| `world.alive` | ecological | 2 | 0.5000% |
| `world.mean_energy` | process | 0.01 | 0.0000% |
| `evolution.environment_resource_effective_dimensions` | ecological | 0.02 | 0.0000% |
| `derived.harvest_extraction_efficiency_window` | mechanistic | 0.005 | 0.0000% |
| `evolution.knowledge_effective_transferred_roots` | ecological | 2 | 1.0000% |
| `evolution.effective_lineages` | ecological | 0.05 | 0.0000% |
| `evolution.functional_harvest_preference_effective_dimensions` | mechanistic | 0.02 | 0.0000% |

| Effect | Classification | Mechanistic | Ecological | Contextual | Footprint | Cross-lineage | Duplication |
|---|---|---:|---:|---:|---:|---:|---:|
| `all_module_expression_effect` | provisional-replicated-ecological-effect | True | True | True | False | False | False |
| `module_0_expression_effect` | provisional-replicated-context-dependent-effect | True | False | True | False | False | False |
| `module_1_expression_effect` | provisional-replicated-ecological-effect | True | True | True | False | False | False |
| `module_2_expression_effect` | provisional-replicated-ecological-effect | True | True | True | False | False | False |
| `module_3_expression_effect` | provisional-replicated-ecological-effect | True | True | True | False | False | False |

## Replicated outcome directions

- `all_module_expression_effect`: `world.alive` negative (6/6 material conditions); `world.mean_energy` phase/context dependent; `evolution.environment_resource_effective_dimensions` positive (6/6 material conditions); `derived.harvest_extraction_efficiency_window` positive (5/6 material conditions); `evolution.knowledge_effective_transferred_roots` negative (5/6 material conditions); `evolution.functional_harvest_preference_effective_dimensions` negative (5/6 material conditions)
- `module_0_expression_effect`: `world.alive` phase/context dependent; `world.mean_energy` phase/context dependent; `evolution.environment_resource_effective_dimensions` phase/context dependent; `evolution.knowledge_effective_transferred_roots` phase/context dependent; `evolution.functional_harvest_preference_effective_dimensions` negative (5/6 material conditions)
- `module_1_expression_effect`: `world.alive` phase/context dependent; `world.mean_energy` phase/context dependent; `evolution.environment_resource_effective_dimensions` positive (6/6 material conditions); `derived.harvest_extraction_efficiency_window` phase/context dependent; `evolution.knowledge_effective_transferred_roots` negative (6/6 material conditions); `evolution.functional_harvest_preference_effective_dimensions` negative (5/6 material conditions)
- `module_2_expression_effect`: `world.alive` negative (5/6 material conditions); `world.mean_energy` positive (5/6 material conditions); `evolution.environment_resource_effective_dimensions` phase/context dependent; `derived.harvest_extraction_efficiency_window` positive (4/6 material conditions); `evolution.knowledge_effective_transferred_roots` phase/context dependent; `evolution.functional_harvest_preference_effective_dimensions` phase/context dependent
- `module_3_expression_effect`: `world.alive` negative (5/6 material conditions); `evolution.environment_resource_effective_dimensions` positive (6/6 material conditions); `derived.harvest_extraction_efficiency_window` positive (4/6 material conditions); `evolution.knowledge_effective_transferred_roots` negative (6/6 material conditions); `evolution.functional_harvest_preference_effective_dimensions` negative (6/6 material conditions)

## Lineage guard

- median effective lineages: `2.0260`
- minimum effective lineages: `1.5744`
- dominant-lineage risk: `True`

## Recommendation

`refresh-immediate-footprints-before-duplication-decision`

A numerical difference is not automatically a practical effect. Practical thresholds screen deterministic paired branches; replication and direct checkpoint footprint are separate requirements. Endpoint sign changes may reflect genuine context dependence or amplified trajectory divergence. Duplication remains blocked when footprint is unavailable, effects are not cross-lineage, or the source population is lineage-dominated.
