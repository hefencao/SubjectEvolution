# SubjectEvolution v0.137.0

SubjectEvolution is a deterministic CPU/GPU ecological evolution simulator with a partitioned unified Subject Graph VM research track.

Version 0.137.0 implements **Subject VM Stage 3C-23: dual-readout rank reachability audit**. The fixed short-study bootstrap now supports a common second readout-only node for an explicit experiment arm. Port 29 remains the Stage 3C-21 uncertainty-mean readout; port 30 is either a duplicate uncertainty coordinate (rank-one control) or the data-screened `local-resource-ratio-3` objective coordinate (rank-two alternative). Both readout nodes have no action output, local eligibility or fixed value semantics.

Across nine independent sources, the alternative raises association-visible centered rank from one to two in every source and produces 128 unique visible token vectors per source. It does not increase temporary commits, objective-divergent sources or stable objective coordinates. This is an engineering reachability result, not a causal-credit, learning, value or universal-attention result. Permanent parameter retention remains disabled.

## Stage 3C-23 study

The authoritative executable steps live only in [`studies/d1z_subject_vm_stage3c23_dual_readout_rank_v1/workflow.toml`](studies/d1z_subject_vm_stage3c23_dual_readout_rank_v1/workflow.toml). The workflow runs the common rank-one and rank-two arms, reproduces the objective-port screen, verifies pre-bootstrap and read-only-control isolation, and packages only declared evidence files without checkpoints.
