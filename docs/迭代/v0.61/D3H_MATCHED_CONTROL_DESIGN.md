# D3-H matched-orientation acute response design

## Problem

D3-G v1 used three branches: original active, reversed active, and original-orientation neutral. The read-only observer evaluates movement against the branch support field. Therefore the reversed active branch requires a neutral branch whose observer uses the reversed field. Without it, a reversed-minus-neutral difference mixes support execution with observation-orientation change.

## v2 branch contract

Every seed/checkpoint state is restored four times:

| Branch | Support execution | Observer orientation | Interventions |
|---|---|---|---|
| original-support | active | original | none |
| neutral-support | multiplier 1 | original | neutralize |
| reversed-support | active | reversed | reverse |
| reversed-neutral-support | multiplier 1 | reversed | reverse + neutralize |

All branches preserve processing cost, resource and residue fields, genotype, inheritance, policy features, action feasibility, and checkpoint RNG state.

## Identified contrasts

```text
original effect = original-support - neutral-support
reversed effect = reversed-support - reversed-neutral-support
orientation interaction = reversed effect - original effect
```

The panel reports these for resource-move support gain, movement-gradient cosine, and positive-gain fraction.

## Sampling unit

Seed is the independent replication unit. Checkpoints within one seed are nested repeated panels. Movement events and entity-ticks provide measurement support but are not independent replicates.

## Interpretation boundary

A repeated matched acute effect is only evidence that existing policy and state respond differently when support execution is active. It is not evidence of adaptation, migration, specialization, coexistence, ecotypes, trophic transfer, or named roles. Evolutionary interpretation additionally requires generation turnover.
