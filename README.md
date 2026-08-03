# SubjectEvolution v0.142.0

SubjectEvolution is a deterministic CPU/GPU ecological evolution simulator with a partitioned unified Subject Graph VM research track.

Version 0.142.0 implements **Subject VM Stage 3C-28: discrete-state and subject-anchored recurrent-basin audit**. It keeps the frozen Stage 3C-23 rank-two readout and separates a shared first-coordinate codebook, cross-subject transition synchrony, slow subject-specific second-coordinate drift and within-subject winner basins without changing the runtime.

Across nine independent sources, three first-coordinate values are shared by every source, but same-phase transition agreement has no consistent excess over cross-phase agreement. The second visible coordinate is overwhelmingly subject anchored (ICC 0.9966–0.9988). Same-state candidates comprise only 34.7%–44.4% of eligible history, while 67.9%–80.4% of winners use the same state and always choose the nearest second coordinate inside that state. No winner is an exact full-token repeat. This diagnoses a fixed-bootstrap within-subject recurrent geometry only; it does not validate causal credit, learning, value or universal attention, and permanent retention remains disabled.

## Stage 3C-28 study

The authoritative executable steps live only in [`studies/d1z_subject_vm_stage3c28_recurrent_basin_v1/workflow.toml`](studies/d1z_subject_vm_stage3c28_recurrent_basin_v1/workflow.toml). The workflow reruns the frozen rank-one/rank-two panel, re-establishes Stage 3C-23/24/25/26/27 lineage, performs the read-only Stage 3C-28 audit, and packages only declared evidence files without checkpoints.

## Stage 3C-26 study

The authoritative executable steps live only in [`studies/d1z_subject_vm_stage3c26_age_phase_opportunity_v1/workflow.toml`](studies/d1z_subject_vm_stage3c26_age_phase_opportunity_v1/workflow.toml). The workflow reruns the frozen rank-one/rank-two panel, re-establishes Stage 3C-23/24/25 lineage, performs the read-only Stage 3C-26 audit, and packages only declared evidence files without checkpoints.

## Stage 3C-25 study

The authoritative executable steps live only in [`studies/d1z_subject_vm_stage3c25_winner_basin_v1/workflow.toml`](studies/d1z_subject_vm_stage3c25_winner_basin_v1/workflow.toml). The workflow reruns the frozen rank-one/rank-two panel, re-establishes Stage 3C-23/24 lineage, performs the read-only Stage 3C-25 audit, and packages only declared evidence files without checkpoints.

## Stage 3C-24 study

The prior candidate-opportunity and score-margin audit remains available at [`studies/d1z_subject_vm_stage3c24_rank2_selection_v1/workflow.toml`](studies/d1z_subject_vm_stage3c24_rank2_selection_v1/workflow.toml).
