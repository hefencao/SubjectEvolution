# SubjectEvolution v0.140.0

SubjectEvolution is a deterministic CPU/GPU ecological evolution simulator with a partitioned unified Subject Graph VM research track.

Version 0.140.0 implements **Subject VM Stage 3C-26: historical-age and query-phase opportunity audit**. It keeps the frozen Stage 3C-23 rank-two readout and reconstructs every eligible candidate from read-only control checkpoints, separating source-boundary forced assignments, historical age, query phase, raw opportunity and selection rate conditional on eligibility.

Across nine independent sources, 16 of 112 assignments per source are structurally forced because only one historical candidate exists. After those assignments are removed, age-one candidates still have the highest or tied opportunity-normalized selection rate in every source. Reused winners occur earlier than single-use and unselected events, but their conditional selection rate also remains at least as high as single-use winners, so raw opportunity alone is insufficient. This does not validate causal credit, learning, value or universal attention, and permanent retention remains disabled.

## Stage 3C-26 study

The authoritative executable steps live only in [`studies/d1z_subject_vm_stage3c26_age_phase_opportunity_v1/workflow.toml`](studies/d1z_subject_vm_stage3c26_age_phase_opportunity_v1/workflow.toml). The workflow reruns the frozen rank-one/rank-two panel, re-establishes Stage 3C-23/24/25 lineage, performs the read-only Stage 3C-26 audit, and packages only declared evidence files without checkpoints.

## Stage 3C-25 study

The authoritative executable steps live only in [`studies/d1z_subject_vm_stage3c25_winner_basin_v1/workflow.toml`](studies/d1z_subject_vm_stage3c25_winner_basin_v1/workflow.toml). The workflow reruns the frozen rank-one/rank-two panel, re-establishes Stage 3C-23/24 lineage, performs the read-only Stage 3C-25 audit, and packages only declared evidence files without checkpoints.

## Stage 3C-24 study

The prior candidate-opportunity and score-margin audit remains available at [`studies/d1z_subject_vm_stage3c24_rank2_selection_v1/workflow.toml`](studies/d1z_subject_vm_stage3c24_rank2_selection_v1/workflow.toml).
