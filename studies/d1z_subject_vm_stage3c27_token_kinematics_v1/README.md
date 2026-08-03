# Stage 3C-27 token-trajectory kinematics audit

This workflow reruns the frozen Stage 3C-23 rank-one and rank-two arms,
restores Stage 3C-23/24/25/26 lineage, and analyzes only the rank-two read-only
control checkpoints. It separates source-boundary single-candidate selection,
exact latest-on-tie selection and strict age-one score geometry, then measures
the local normalized-token step, turn and first-readout-coordinate recurrence.

It changes no runtime mechanism, token geometry, similarity, threshold,
candidate cardinality, tie-break, update scale, rollback or retention policy.
Queries, events, subjects and windows remain nested observations rather than
independent source replicates.
