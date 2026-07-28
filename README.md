# SE v0.57

SE is a deterministic artificial-life and subject-structure research platform. The main line contains conservative regulatory physiology, inherited delayed resource processing, storage-constrained intake, identity-preserving external raw-material recycling, and an opt-in persistent four-channel abiotic renewal field.

## Why v0.57

The supplied D3-D run completed three 1500-tick seeds. Positive renewal source and negative renewal sink occurred in every seed, external recycling remained conservative, and all final fields retained multiple effective resource dimensions. The old D3-D report nevertheless marked the open external-resource ledger invalid in every seed.

The failure is a measurement-boundary defect rather than evidence of missing ecological material. The environment stores fields as `float32`, while cumulative physical fluxes are accumulated at higher precision. Field renewal/diffusion/clipping and segmented harvest commits therefore produce small signed inventory settlement terms. v0.56 omitted those terms from the authoritative ledger.

v0.57 records two independent numerical settlement terms without changing trajectories:

- field-update settlement: actual post-update inventory minus the inventory implied by source, sink and residue release;
- harvest-commit settlement: actual field removal minus intended admitted harvest.

The corrected ledger is:

```text
initial external resource
+ abiotic renewal source
+ residue release
+ field-update settlement
=
harvested resource
+ abiotic renewal sink
+ final external resource
+ harvest-commit settlement
```

A same-seed 300-tick validation reduced maximum relative ledger residual from about `7.5e-6` to `2.7e-16`. Physical source, sink, release, harvest, final inventory and the simulated trajectory are unchanged.

This release deliberately does not add collection-processing coupling, migration, trophic transfer, resource roles, diversity protection, lineage protection or population feedback. The supplied long run should be rerun with the v2 report schema before the D3-E gate is reconsidered.

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

## Run D3-D

```bash
se-d3-resource-renewal \
  --config configs/mvp_short_d3d_persistent_resource_renewal_longrun.json \
  --seeds 56001,56002,56003 \
  --output analyses/d3d_persistent_resource_renewal_1500_v057 \
  --backend gpu \
  --until-tick 1500
```

D3-D tests persistent role-free external opportunity and open-system accounting. It is not evidence for migration, collection-processing specialization, coexistence, trophic differentiation or named resource roles.

## Current version documents

- [Supplied D3-D result interpretation](docs/v0.57/D3D_SUPPLIED_RESULT_INTERPRETATION.md)
- [Numerical settlement design](docs/v0.57/D3D_NUMERICAL_SETTLEMENT_DESIGN.md)
- [300-tick validation](docs/v0.57/D3D_300_TICK_VALIDATION_REPORT.md)
- [Implementation report](docs/v0.57/IMPLEMENTATION_REPORT.md)
