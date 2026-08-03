# Stage 3C-25 deterministic winner-basin reuse audit

This workflow reruns the frozen Stage 3C-23 rank-one and rank-two arms, restores
Stage 3C-23/24 lineage, and then analyzes only the rank-two read-only control
checkpoints.  It separates absolute and score-spread-normalized winner margins,
historical-event eligibility opportunity, and reuse of one winner across
multiple distinct query events and visible query vectors.

It changes no runtime mechanism, token geometry, similarity, threshold,
candidate cardinality, tie-break, update scale, rollback or retention policy.
Queries, events, subjects and windows remain nested observations rather than
independent source replicates.
