# SubjectEvolution v0.135.0

SubjectEvolution is a deterministic CPU/GPU ecological evolution simulator with a partitioned unified Subject Graph VM research track.

Version 0.135.0 implements **Subject VM Stage 3C-21: subject/event-specific objective-input readout audit**. Both paired arms use the same nine-node fixed bootstrap graph and the same readout-only node 8. The only changed factor is whether that node reads objective input port 0 (`constant-one`) or port 11 (`uncertainty-mean`) before emitting to association-visible token port 29.

The uncertainty readout creates subject-specific and event-time-varying token geometry without changing action output. It remains a replaceable bootstrap shaping bias: uncertainty has no fixed value semantics, the result does not validate causal credit or learning, and permanent parameter retention remains disabled.

## Stage 3C-21 study

The authoritative executable steps live only in [`studies/d1z_subject_vm_stage3c21_subject_event_readout_v1/workflow.toml`](studies/d1z_subject_vm_stage3c21_subject_event_readout_v1/workflow.toml). The workflow runs the constant and uncertainty readout arms, verifies source and read-only objective-behavior identity, produces Stage 3C-7/8/10 evidence and packages only declared files without checkpoints.
