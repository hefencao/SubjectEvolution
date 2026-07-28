# SE v0.58

SE is a deterministic artificial-life and subject-structure research platform. The current main line combines conservative regulatory physiology, inherited delayed resource processing, storage-constrained intake, identity-preserving external raw-material recycling, persistent four-channel abiotic renewal, and an opt-in costed spatial processing substrate.

## Why v0.58

The supplied D3-D v2 rerun completed seeds `56001`, `56002`, and `56003` to tick 1500. The corrected external-resource ledger and external-recycling ledger close in every seed, while final resource effective dimensions remain about `2.86`–`2.98`. This clears the measurement gate for a minimal collection-processing coupling, but it does not establish migration, specialization, coexistence, trophic transfer, or ecological roles.

D3-E introduces a role-free abiotic processing-support field:

- it reuses the persistent four-channel wave basis with a quarter-cycle phase shift;
- it changes only conversion throughput of raw material already held in internal stores;
- every converted unit pays a configured energy cost before body outcomes are realized;
- energy shortage scales all candidate channel conversions proportionally;
- `neutralize-spatial-processing-support` fixes support at `1.0` while preserving costs, genes, resource fields, and checkpoint state;
- the paired experiment restores both branches from the same tick-0 full-world checkpoint.

No reward is added for moving, maintaining diversity, surviving, specializing, or occupying a particular location. The new experiment reports paired differences but does not turn finite-seed signs into ecological claims.

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

## Run D3-E

```bash
se-d3-spatial-processing \
  --config configs/mvp_short_d3e_spatial_processing_longrun.json \
  --seeds 58001,58002,58003 \
  --output analyses/d3e_spatial_processing_1500 \
  --backend gpu \
  --until-tick 1500
```

Each seed produces an active spatial-support branch and a cost-preserving neutral-support branch from one shared tick-0 checkpoint.

## Current version documents

- [D3-E design](docs/v0.58/D3E_SPATIAL_PROCESSING_DESIGN.md)
- [Supplied D3-D v2 result](docs/v0.58/D3D_SUPPLIED_RESULTS_V2.md)
- [Implementation report](docs/v0.58/IMPLEMENTATION_REPORT.md)
