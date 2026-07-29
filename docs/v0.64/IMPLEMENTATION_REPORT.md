# v0.64 implementation report

## Baseline and supplied overlay

- sole project baseline: `se_v063_project.zip`;
- supplied overlay: `fixed(1).zip`;
- supplied runtime result: `analyses(10).zip`;
- overlay files were copied by their archive-relative paths before any further edits.

## Integrated corrections

### GPU oxygen-gradient semantics

v0.63 applied a host-side oxygen steering correction after the GPU policy decision had already been computed and downloaded. The overlay moves oxygen-gradient augmentation into `HybridGpuRuntime.prepare`, before policy evaluation. The CPU and GPU policies therefore consume the corresponding augmented resource gradient at the same semantic boundary.

### Working-memory learning boundary

The exact state features used for working-memory routing are now retained in `GpuPreparedStep` and passed to the later learning update. They are no longer recomputed after CPU-side state may have advanced.

### Checkpoint semantic exclusions

`entity_device_version` and `last_information` remain checkpointed for restoration and diagnostics, but are not treated as backend-neutral continuation semantics:

- device mirror sequence numbers are validated by the dedicated persistent-device stage;
- observations are validated by `policy-observation` and related stages;
- the recursive semantic checkpoint stage excludes only the explicitly registered backend/cache roots.

### First-divergence identity

Entity mismatch reports now include IDs from both CPU and candidate worlds instead of reading both IDs from the CPU world.

## Supplied GPU result audit

The supplied result contains 32 panels and 128 branch runs. Every branch records real hybrid acceleration and no fallback. One panel is acute-ineligible solely because two active branches dip to 99 alive. All completed branch resource and recycling ledgers remain valid.

The matched effect remains unreplicated:

- original equal-seed mean gain: `-7.585360200717007e-07`;
- reversed equal-seed mean gain: `-4.841683726372987e-08`;
- both-positive seed fraction: `0.25`;
- replication gate: `false`.

## Operational audit additions

### `gpu-execution-audit-v1`

`se-gpu-execution-audit` recursively finds run records with backend provenance and reports:

- requested and actual backend counts;
- accelerated, strict-reference, fallback and CPU-authoritative counts;
- median/mean/min/max step, window, phase and transfer diagnostics;
- experiment panel/eligibility counts when available;
- failed backend records without converting them into scientific exclusions.

### `gpu-parity-certificate-v1`

When `SE_GPU_PARITY_REPORT_DIR` is set by `make parity-gpu`, `tests/test_parity.py` writes:

- one real-device stage-parity report;
- one CPU/GPU world-parity report for every entry in `SEMANTIC_PARITY_CONFIGS`.

`scripts/summarize_gpu_parity_reports.py` fails if any report is absent, unavailable or failed. It never accepts stale partial output because the Makefile clears the report directory before execution.

## Interpretation boundary

The supplied artifacts prove actual hybrid GPU execution. They do not, by themselves, prove target-device parity or speedup. The delivery host has no usable CUDA/CuPy device, so real-device parity remains a target-host release gate.
