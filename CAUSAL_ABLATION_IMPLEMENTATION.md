# Working-Memory and Sparse-Selection Causal Ablations — v0.14.0

## Purpose

v0.14 adds two scientific checkpoint interventions so the effects of memory
and sparse selection can be separated from the existence of knowledge itself.
Both interventions branch from a full `.sechk` checkpoint, retain stable IDs
and the run seed, and do not replace carrier actions directly.

## `ablate-working-memory`

At the branch tick this intervention:

1. clears all quantized working-memory coordinates;
2. clears previous-observation memory used by the update rule;
3. clears the public float memory view;
4. freezes future working-memory updates in the branch;
5. leaves genotype, knowledge copies, latent contents, and physical world state
   otherwise unchanged at the intervention boundary.

Subsequent action differences therefore measure the combined causal role of
stored working-memory state and its future updates. The branch also avoids
future working-memory computation costs, which must be considered when
interpreting physical outcomes.

## `bypass-sparse-selection`

This intervention disables only the ephemeral Top-k filter. All matching
knowledge copies are passed to the existing L2 router.

It does **not**:

- remove knowledge copies;
- change holder byte capacity;
- alter confidence or local outcomes;
- modify content lineage;
- disable the latent router;
- directly choose an action.

Selection computation cost is no longer charged after the intervention, while
routing cost generally increases because more copies reach L2.

## Checkpoint semantics

The ablation flags are part of semantic world state:

```text
working_memory_ablation_enabled
sparse_selection_ablation_enabled
```

They are preserved by clone, full checkpoint, restore, and paired replay.
Historical checkpoints without these fields restore both flags as `False`.

## Scientific interpretation

These are causal module interventions, not claims that the modules are
beneficial or harmful. A single paired branch can show that a mechanism changes
world outcomes under common prehistory and stable random streams. Adaptive
value requires multiple seeds, intervention ticks, environments, and matched
cost budgets.
