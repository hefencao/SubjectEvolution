# Stage 3C-28 discrete-state and subject-anchored recurrent-basin audit

This workflow reruns the frozen Stage 3C-23 rank-one and rank-two arms,
restores Stage 3C-23/24/25/26/27 lineage, and analyzes only the rank-two
read-only control checkpoints. It separates a shared discrete first-coordinate
codebook, cross-subject transition synchrony, slow subject-specific movement in
the second coordinate, and within-subject recurrent winner basins.

It changes no runtime mechanism, token geometry, similarity, threshold,
candidate cardinality, tie-break, update scale, rollback or retention policy.
Queries, events, subjects and windows remain nested observations rather than
independent source replicates.
