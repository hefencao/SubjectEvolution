# SE v0.67

SE is a deterministic artificial-life and subject-structure research platform. The current main line retains four role-free resource channels, conservative delayed storage and processing, identity-preserving external recycling, persistent abiotic renewal, costed spatial processing support, matched controls and GPU-first execution.

## Why v0.67

An 8,000-entity run that rapidly contracts toward roughly 1,000 entities can be dominated by an early demographic bottleneck, founder sampling and drift before meaningful generation turnover. Extending the same trajectory to a large tick count does not by itself turn it into effective evolutionary-selection evidence.

v0.67 adds a non-intervening demographic-selection validity boundary. Runtime diagnostics now preserve canonical death causes, population fraction relative to initialization, cumulative replacement and generation depth. The new `se-selection-validity-audit` keeps every failed run and window, treats the seed as the independent unit, and distinguishes mechanism-valid trajectories from population-supported and generation-supported selection evidence.

No population is rescued. No death, birth, resource, carrying-capacity, reward, sensing, diversity or lineage-protection parameter is altered.

## Demographic-selection audit

Run the fixed scale-4 diagnostic source:

```bash
se-multi \
  --config configs/mvp_d3j_gpu_scale4_demographic_audit.json \
  --seeds 67001,67002,67003 \
  --output analyses/d3j_scale4_demography \
  --backend auto \
  --until-tick 1200
```

Then audit the fixed seed outputs:

```bash
se-selection-validity-audit \
  --run 67001=analyses/d3j_scale4_demography/seed_67001 \
  --run 67002=analyses/d3j_scale4_demography/seed_67002 \
  --run 67003=analyses/d3j_scale4_demography/seed_67003 \
  --output analyses/d3j_scale4_demography/selection_validity
```

The default interpretation floor is 25% of the initial population, together with effective-lineage, parent-sample and generation-turnover requirements. These thresholds change interpretation only and never feed back into the world.

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

- [Implementation report](docs/v0.67/IMPLEMENTATION_REPORT.md)
- [Demographic-selection plan](docs/v0.67/DEMOGRAPHIC_SELECTION_PLAN.md)
- [Protocol audit](docs/v0.67/protocol_audit.md)
