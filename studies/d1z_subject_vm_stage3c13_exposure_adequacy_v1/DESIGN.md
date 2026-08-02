# Stage 3C-13 design

This study changes one experimental quantity: the guarded temporary-write rollback duration from two ticks to three ticks. The paired read-only control horizon is synchronized to the same value because Stage 3C-5 already requires it to equal rollback duration; it is not an independent factor.

Both arms use the same project config, ordered nine-seed panel, source tick, 32-entity population, 16 fixed-bootstrap subjects, eight-tick branch horizon, bounded update scale, trace retention and bootstrap topology. The source checkpoint is created before applying the branch-only exposure override. Each seed must therefore have the same source state hash, source config hash and bootstrap lineage in both arms.

The assessment also compares objective and action-producing trace arrays in the two read-only control branches. Exposure timing may alter reservation bookkeeping, but must not alter read-only control behavior. Windows remain nested within stable subjects and source checkpoints; the independent replicate remains the source checkpoint.

The study does not authorize permanent retention, automatic keep/revert, scalar reward, topology evolution, universal-attention claims, learning claims or Epoch 1 entry.
