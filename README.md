# SE v0.55

SE is a deterministic artificial-life and subject-structure research platform. The current main line now contains a conservative chain from external resources to inherited internal storage, delayed conversion, storage-constrained intake, and an opt-in external residual-material cycle.

## Why v0.55

The supplied three-seed D3-B run is valid. Intake and internal-store ledgers close in every seed. The reported post-assimilation overflow is only about `6e-9`–`9e-9` of per-channel harvested mass; the previous `False` summary came from comparing a 1500-tick accumulated float residual with a fixed absolute zero threshold.

v0.55 therefore:

- changes D3-B result interpretation to a scale-aware tolerance;
- adds an explicit assessment command for archived D3-B results;
- adds opt-in resource-v6 external recycling;
- sends internal-store decay and raw stores carried at death into a local four-channel residual-material field;
- preserves resource identity through deposition, diffusion and release;
- enforces at least one tick of external residence before release;
- limits release by free capacity in the same external resource channel;
- adds no decomposer, scavenger, trophic role, diversity reward or lineage protection;
- preserves resource-v5 exactly when external recycling is disabled;
- checks project/package/Makefile version consistency before `conda-sync`.

## Workflow

After metadata, entry-point or dependency changes:

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

## Reassess the supplied D3-B run

```bash
se-d3-conservative-intake-assess \
  --results analyses/d3b_conservative_intake_1500/d3_conservative_intake_results.json \
  --output analyses/d3b_conservative_intake_assessment
```

## Run D3-C

```bash
se-d3-external-recycling \
  --config configs/mvp_short_d3c_external_recycling_longrun.json \
  --seeds 55001,55002,55003 \
  --output analyses/d3c_external_recycling_1500 \
  --backend gpu \
  --until-tick 1500
```

D3-C establishes a generic external material-return substrate. It is not evidence for decomposers, scavenging, trophic differentiation, migration, coexistence or module-copy benefit.

## Current version documents

- [D3-B scale-aware reassessment](docs/v0.55/d3_conservative_intake_assessment.md)
- [D3-C design](docs/v0.55/D3C_EXTERNAL_RECYCLING_DESIGN.md)
- [D3-C run plan](docs/v0.55/D3C_EXTERNAL_RECYCLING_PLAN.md)
- [Implementation report](docs/v0.55/IMPLEMENTATION_REPORT.md)
