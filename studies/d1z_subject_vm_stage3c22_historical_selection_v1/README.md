# Stage 3C-22 selected historical-event coverage and reuse audit

This workflow reruns the frozen Stage 3C-21 constant-one and uncertainty-mean
readout arms, reconstructs every delay-valid and above-threshold historical
candidate from read-only control checkpoints, and separately reports selected
event identity coverage, repeated selection and objective-fact span.

It does not change addressing, candidate cardinality, similarity, update scale,
rollback, retention or permanent-write policy. Distinct event identities,
subjects and windows remain nested observations rather than independent source
replicates.
