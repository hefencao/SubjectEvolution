# Evolvable Sparse Selection Capacity — v0.14.0

## Purpose

v0.13 introduced a stable sparse Query–Key selector, but its `K` was a global
configuration constant. v0.14 makes selection capacity an optional inherited
entity trait without turning the temporary Top-k workset into authoritative
knowledge storage.

The scientific question is no longer only “which copies score highest?” but
also “how much knowledge-routing capacity is worth paying for under local
selection pressure?”

## Schemas

Legacy semantics remain available:

```text
sparse_selection_capacity_schema = fixed-config-topk-v1
sparse_selection_top_k = K
```

The new schema is:

```text
sparse_selection_capacity_schema = inherited-discrete-topk-v1
sparse_selection_capacity_levels = [0, 1, 2, 4, 8]
```

Only the inherited schema adds one genome coordinate. Existing K1–K4, L1/L2,
working-memory, and fixed-Top-k genome layouts remain unchanged.

## Inherited mapping

The capacity gene is clipped to `[-1, 1]` and mapped deterministically to an
index in the ordered configured level table. The gene does not encode category
meaning or action preference. It controls only the maximum number of copies
that the entity is willing to route in that tick.

The selected count is:

```text
selected_count = min(inherited_top_k, matching_candidate_count)
```

`K=0` has explicit semantics:

- matching candidates are still inspected and selection work is charged;
- no copy enters the temporary router workset;
- authoritative copies remain stored, maintainable, transferable, and
  mutable;
- no knowledge residual is published for that entity in the tick.

## Stability and GPU boundary

Query–Key scores remain integer. Per-entity ordering remains:

```text
(-score_q, copy_id, content_id)
```

This makes ties stable and independent of input array permutation. The capacity
trait is resolved on the CPU-reference publication boundary. A future GPU
implementation may batch the selected workset, but cannot redefine the ordered
selection semantics.

## Costs

No extra hand-authored “capacity penalty” is required. The existing physical
ledger already charges the consequences of choosing a larger K:

- candidate inspection cost;
- selected-copy cost;
- latent dimensions processed;
- L2 MAC count;
- active hidden units;
- emitted residual cells;
- saturation and clipping overhead.

A larger inherited K therefore increases expression opportunity and generally
increases computation cost. A smaller K saves computation but can suppress
useful knowledge. This is the intended evolutionary tradeoff.

## Audit fields

New diagnostics include:

```text
selection_requested_top_k
selection_requested_top_k_sum
selection_zero_capacity_entities
sparse_selection_capacity_schema
sparse_selection_capacity_levels
sparse_selection_capacity_gene_index
```

They are written to routing-cost, policy-contribution, selection-event,
metrics, and run-manifest outputs where applicable.

## Authority boundary

The following remain authoritative:

- dynamic knowledge copy arena;
- variable-length latent content store;
- copy verification and outcome state;
- content/variant lineage;
- holder capacity and physical byte costs.

The selected Top-k matrix remains an ephemeral workset. Changing the inherited
capacity does not delete, truncate, merge, or reclassify knowledge.
