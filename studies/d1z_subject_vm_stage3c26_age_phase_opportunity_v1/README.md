# Stage 3C-26 historical-age and query-phase opportunity audit

This workflow reruns the frozen Stage 3C-23 rank-one and rank-two arms, restores
Stage 3C-23/24/25 lineage, and analyzes only the rank-two read-only control
checkpoints. It separates source-boundary queries with one eligible candidate,
historical-age-conditioned selection, query-phase winner age, raw historical
event opportunity and selection rate conditional on eligibility.

It changes no runtime mechanism, token geometry, similarity, threshold,
candidate cardinality, tie-break, update scale, rollback or retention policy.
Queries, events, subjects and windows remain nested observations rather than
independent source replicates.
