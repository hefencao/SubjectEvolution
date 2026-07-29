# SE v0.60

SE is a deterministic artificial-life and subject-structure research platform. The current main line combines conservative regulatory physiology, inherited delayed resource processing, storage-constrained intake, identity-preserving external raw-material recycling, persistent four-channel abiotic renewal, costed spatial processing support, and shared-checkpoint response measurement.

## Why v0.60

The supplied D3-F three-seed panel completed all original, reversed, and neutral branches to tick 1500, with valid resource and recycling ledgers. Its cumulative response statistics are nevertheless dominated by the early high-population transient:

- the first 300 ticks contribute about 43.7%–53.7% of inventory-eligible entity-ticks;
- the first 300 ticks contribute about 52.8%–61.3% of resource movements;
- every branch first falls below 100 alive between observed ticks 330 and 420;
- movement events are repeated observations nested inside only three independent seed triplets.

v0.60 therefore does not add another ecological mechanism. It adds D3-G, a preregistered acute checkpoint-panel protocol and explicit sampling-adequacy analysis.

## D3-G

`se-d3-processing-response-panel` runs one unintervened source trajectory per seed to every predeclared checkpoint. Each available checkpoint is restored into original-support, reversed-support, and neutral-support branches for a short response window.

The result records:

- checkpoint population size, effective lineages, lineage concentration, age and generation depth;
- exact branch-window alive entity-ticks and inventory-eligible entity-ticks;
- resource movement counts and unique observed entities;
- effective lineage entity-ticks and largest-lineage contribution;
- windowed response trajectories rather than only one tick-0 cumulative mean;
- checkpoint-relative external-resource and recycling ledgers;
- separate acute-response and evolutionary-sampling eligibility.

Every predeclared checkpoint remains in the result. Low-population or unavailable checkpoints are not replaced, retried, or removed. Eligibility controls interpretation only and never feeds back into the world.

`se-d3-response-adequacy` performs the same fixed-block audit on historical D3-F result files.

## Workflow

After metadata, entry-point, dependency, or package-layout changes:

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

## Audit the supplied D3-F result

```bash
se-d3-response-adequacy \
  --results d3_processing_response_results.json \
  --output analyses/d3f_sampling_adequacy.json \
  --block-ticks 300 \
  --min-alive 100 \
  --burn-in-ticks 300
```

## Run the base D3-G panel

```bash
se-d3-processing-response-panel \
  --config configs/mvp_short_d3e_spatial_processing_longrun.json \
  --seeds 60001,60002,60003 \
  --output analyses/d3g_response_panel_base \
  --checkpoint-ticks 300,600,900,1200 \
  --response-window 120 \
  --observation-period 30 \
  --backend gpu
```

Map-scale controls are provided as:

- `configs/mvp_short_d3g_spatial_processing_scale1p5_longrun.json`;
- `configs/mvp_short_d3g_spatial_processing_scale2_longrun.json`.

They preserve entity density, maximum-entity density and grid-cell physical size. They do not protect populations or lineages.

## Current version documents

- [D3-G design](docs/v0.60/D3G_SAMPLE_SUPPORT_DESIGN.md)
- [Supplied D3-F result](docs/v0.60/D3F_SUPPLIED_RESULTS.md)
- [Supplied-result adequacy audit](docs/v0.60/D3F_SUPPLIED_SAMPLING_ADEQUACY_AUDIT.md)
- [Base 300→420 pilot](docs/v0.60/D3G_BASE_300_120_PILOT_RESULTS.md)
- [Implementation report](docs/v0.60/IMPLEMENTATION_REPORT.md)
