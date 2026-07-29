# SE v0.64

SE is a deterministic artificial-life and subject-structure research platform. The current main line retains four role-free resource channels, conservative delayed storage and processing, identity-preserving external recycling, persistent abiotic renewal, costed spatial processing support, matched controls and nested shared-checkpoint response measurement.

## Why v0.64

The user-supplied parity fixes are integrated into the GPU path. They move oxygen-gradient augmentation into the prepared GPU observation boundary, preserve the exact working-memory state features used by later learning, and keep backend-only mirror sequencing and observation snapshots out of checkpoint-semantic comparison while retaining their dedicated parity stages.

The supplied 1.5× rerun contains 128 completed branches. Every branch records:

```text
execution_backend: gpu-hybrid-accelerated
gpu_acceleration_enabled: true
gpu_fallback_used: false
```

The operational problem from v0.63 is therefore resolved: the experiment actually executes the hybrid GPU path. Scientific and performance gates remain separate. Thirty-one of 32 panels are acute eligible, zero checkpoints are evolutionarily eligible, and the directional response replication gate remains false.

At the late low-population response windows represented in the supplied artifacts, the median reported time per tick is about 0.0906 seconds on hybrid GPU versus 0.0282 seconds in the earlier strict-reference CPU run. This is an observational comparison across different seeds, not a paired benchmark or a general GPU-speed claim. It shows why execution provenance and performance must both be audited.

## GPU execution and parity

Normal runs default to `--backend auto`:

```bash
se-d3-processing-response-panel \
  --config configs/mvp_short_d3g_spatial_processing_scale1p5_longrun.json \
  --seeds 63001,63002,63003,63004,63005,63006,63007,63008 \
  --output analyses/d3i_response_panel_1p5_gpu \
  --checkpoint-ticks 300,600,900,1200 \
  --response-window 120 \
  --observation-period 30
```

Before scientific use on a new CUDA/CuPy stack:

```bash
make parity-gpu
```

The target writes one machine-readable report for GPU stage parity and one for every registered semantic-family world. A certificate is created only when all required reports are present and pass.

Audit an experiment artifact independently of scientific interpretation:

```bash
se-gpu-execution-audit \
  --result panel=analyses/d3i_response_panel_1p5_gpu/d3_processing_response_panel_results.json \
  --output analyses/gpu_execution_audit
```

`gpu-execution-audit-v1` verifies recorded backend provenance and summarizes timing and transfer diagnostics. It does not replace `tests/test_parity.py` and does not establish speedup.

## Parity v2

`cpu-gpu-parity-v2` validates:

- stage-by-stage observation, policy, intent and world outputs;
- all checkpoint-authoritative semantic leaves through recursive state comparison;
- persistent GPU mirrors for entity, social, environment and information state;
- representative semantic families covering knowledge/culture, mortality/adaptive groups, D3 processing, subject/multi-environment and plugins;
- exact discrete comparisons and tolerance-bounded floating comparisons;
- first divergent stage, leaf and reference/candidate entity IDs.

Backend mirror sequence numbers and diagnostic observation snapshots remain checkpointed for restoration and audit but are compared in their dedicated stages rather than treated as cross-backend continuation semantics.

## Supplied D3-I fixed-GPU result

The nested matched audit reports:

```text
acute eligible panels: 31 / 32
independent seeds:      8
original mean gain:    -7.585360200717007e-07
reversed mean gain:    -4.841683726372987e-08
both-positive seeds:    0.25
replication gate:       false
evolutionary eligible:  0
```

The one ineligible panel misses the preregistered minimum-alive threshold because two active branches reach 99 alive; its resource and recycling ledgers remain valid. No support sensor, movement reward, migration controller or ecological mechanism is unlocked.

## Workflow

After metadata, entry-point, dependency or package-layout changes:

```bash
make conda-sync
```

Daily validation:

```bash
make test
make conda-check
```

Artifact audit:

```bash
make release-check
```

## Current version documents

- [Implementation report](docs/v0.63/IMPLEMENTATION_REPORT.md)
- [Supplied D3-I effect audit](docs/v0.63/SUPPLIED_D3I_EFFECT_AUDIT.md)
- [Supplied GPU execution audit](docs/v0.63/SUPPLIED_GPU_EXECUTION_AUDIT.json)
- [No-GPU fallback smoke manifest](docs/v0.63/AUTO_BACKEND_SMOKE_MANIFEST.json)
