# SE v0.63

SE is a deterministic artificial-life and subject-structure research platform. The current main line retains four role-free resource channels, conservative delayed storage and processing, identity-preserving external recycling, persistent abiotic renewal, costed spatial processing support, matched controls and nested shared-checkpoint response measurement.

## Why v0.63

The supplied D3-I replication contains eight independent seeds at each of the 1.5× and 2× scales. All 64 matched panels are acute eligible, but neither scale passes the directional replication gate. v0.63 therefore adds no world mechanism.

The supplied run manifests also show that every one of 256 branches requested `gpu` but executed `gpu-strict-reference` with `gpu_acceleration_enabled=false`. The previous default validated GPU availability while leaving the CPU world authoritative, which is unsuitable for larger long-running panels.

v0.63 changes the operational boundary:

- high-level commands default to `--backend auto`;
- a usable CUDA/CuPy device selects the real `gpu-hybrid-accelerated` path;
- a machine without a usable GPU falls back to CPU and records `cpu-fallback-no-gpu` and the reason;
- `strict-reference` remains available only as an explicit historical diagnostic;
- `tests/test_parity.py` owns CPU/GPU semantic validation.

## GPU execution

Normal runs no longer need a backend flag:

```bash
se-d3-processing-response-panel \
  --config configs/mvp_short_d3g_spatial_processing_scale1p5_longrun.json \
  --seeds 63001,63002,63003,63004,63005,63006,63007,63008 \
  --output analyses/d3i_response_panel_1p5_gpu \
  --checkpoint-ticks 300,600,900,1200 \
  --response-window 120 \
  --observation-period 30
```

Before a scientific long run on a new CUDA/CuPy stack, execute the parity suite:

```bash
make parity-gpu
```

On a GPU host, the real-device semantic-family tests must run rather than skip. Inspect each run's `run_manifest.json`:

```text
execution_backend: gpu-hybrid-accelerated
gpu_acceleration_enabled: true
gpu_fallback_used: false
```

On a host without a usable GPU the run continues on CPU and records the fallback explicitly. A low-level device-only test can still call `resolve_backend("gpu")`, which remains strict and never silently returns CPU.

## Parity v2

`cpu-gpu-parity-v2` validates more than a final summary curve:

- existing stage-by-stage policy, observation, intent and world comparisons;
- all checkpoint-authoritative semantic leaves through recursive state comparison;
- persistent GPU mirrors for entity, social, environment and information state;
- representative semantic families covering knowledge/culture, mortality/adaptive groups, D3 processing, subject/multi-environment and plugins;
- exact discrete comparisons and tolerance-bounded floating comparisons;
- first divergent stage and leaf reporting.

Adding checkpoint-authoritative state automatically expands the complete semantic-state parity comparison unless the field is explicitly classified as a backend cache.

## Supplied D3-I result

The supplied nested audit reports:

```text
1.5x original gain: -2.898296122704174e-06
1.5x reversed gain: -5.477934432784455e-06
2x original gain:    9.253429667044727e-07
2x reversed gain:    6.064305225430936e-07
replication gates:   false, false
```

Movement events and checkpoints remain nested observations, not independent seeds. These results do not justify a support sensor, movement reward, migration controller or ecological claim.

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
