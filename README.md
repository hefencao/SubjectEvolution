# SE v0.66

SE is a deterministic artificial-life and subject-structure research platform. The current main line retains four role-free resource channels, conservative delayed storage and processing, identity-preserving external recycling, persistent abiotic renewal, costed spatial processing support, matched controls and nested shared-checkpoint response measurement.

## Why v0.66

v0.66 integrates the supplied scale-4 GPU/knowledge optimizations and fixes the
reporting boundary exposed by the two completed 3,000-tick runs. Hybrid runs
intentionally keep environment fields device-resident between checkpoints, but
`summary.json` previously combined the current entity/tick counters with the
most recently materialized host residue mirror. Changing checkpoint cadence
therefore changed summary freshness without changing the final tick.

Every metrics row and final summary now uses an
`authoritative-reporting-snapshot-v1` boundary: current device state is
materialized before the row is assembled, and the row records
`reporting_state_tick` and `reporting_state_source`. Summary correctness is no
longer coupled to checkpoint cadence.

Every `Simulation.run()` also writes `run_plan.json` before the first
authoritative step. The plan records the fixed target tick, reporting cadence,
checkpoint cadence, resolved backend and config hash; it never adapts the
schedule from observed outcomes.

The supplied staged files additionally retain 100-tick full checkpoints, disable
large dense audit CSV streams, and batch deterministic latent-root hash work on
the selected device. No world, reward, sensing, inheritance, population-support
or ecological mechanism changes in this release.

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

- [Implementation report](docs/v0.66/IMPLEMENTATION_REPORT.md)
- [Supplied scale-4 summary audit](docs/v0.66/SUPPLIED_SCALE4_SUMMARY_AUDIT.md)
- [Protocol audit](docs/v0.66/protocol_audit.md)
