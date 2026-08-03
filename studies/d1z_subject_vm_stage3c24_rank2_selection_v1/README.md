# Stage 3C-24 rank-two selection coverage and score-margin audit

This workflow reruns the frozen Stage 3C-23 rank-one duplicate-coordinate and
rank-two selected-coordinate arms. It reconstructs every delay-valid,
non-zero, above-threshold candidate from read-only control checkpoints, then
separately measures exact best-score ties, best-versus-second margins, selected
historical-event identity coverage and reuse concentration.

It changes no runtime mechanism, similarity, threshold, candidate cardinality,
tie-break, update scale, rollback, retention or permanent-write policy.
Subjects, events and windows remain nested observations rather than independent
source replicates.
