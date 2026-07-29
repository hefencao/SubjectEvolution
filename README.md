# SE v0.65

SE is a deterministic artificial-life and subject-structure research platform. The current main line retains four role-free resource channels, conservative delayed storage and processing, identity-preserving external recycling, persistent abiotic renewal, costed spatial processing support, matched controls and nested shared-checkpoint response measurement.

## Why v0.65

v0.65 advances the large-population GPU path rather than treating late 100–300 entity windows as a performance gate. The CPU remains authoritative for action settlement and lifecycle, while regular observation preprocessing now stays on the selected device:

- fixed-budget resource-affinity quantization;
- fixed-budget danger-evidence quantization;
- affinity/storage-conditioned policy resource view;
- oxygen-gradient construction;
- information detection summaries when full parity/evaluation diagnostics are not due.

The runtime reports both actual transfer bytes and the semantic host traffic avoided by this device-resident boundary. No world, reward, sensing, inheritance or ecological mechanism changes in this release.

Two density-preserving large-run presets are included:

```bash
se --config configs/mvp_d3i_gpu_scale4_longrun.json \
  --output runs/d3i_gpu_scale4 --backend auto

se --config configs/mvp_d3i_gpu_scale8_longrun.json \
  --output runs/d3i_gpu_scale8 --backend auto
```

They start with 8,000 and 32,000 entities respectively, use real hybrid GPU execution when available, disable per-tick invariant validation, and leave semantic validation to the target-device parity suite.

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

## Existing D3-I response result

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

- [Implementation report](docs/v0.65/IMPLEMENTATION_REPORT.md)
- [Supplied D3-I effect audit](docs/v0.65/SUPPLIED_D3I_EFFECT_AUDIT/d3_response_scale_audit.md)
- [Supplied GPU execution audit](docs/v0.65/SUPPLIED_GPU_EXECUTION_AUDIT/gpu_execution_audit.json)
