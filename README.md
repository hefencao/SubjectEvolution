# SE v0.56

SE is a deterministic artificial-life and subject-structure research platform. The main line now contains conservative regulatory physiology, inherited delayed resource processing, storage-constrained intake, identity-preserving external raw-material recycling, and an opt-in persistent four-channel abiotic renewal field.

## Why v0.56

The supplied D3-C run closes the external residue cycle in all three 1500-tick seeds, so the recycling substrate is retained. Its remaining limitation is environmental: the final four resource fields have only about `1.11`–`1.19` effective dimensions and mean absolute channel correlations around `0.88`–`0.92`.

The cause is structural. `orthogonal-four-resource-niche-v1` uses channel-specific geometry for initialization, but its logistic regeneration equilibrium is the same uniform capacity in every cell. Common entity depletion can therefore erase the initial opportunity structure.

v0.56 adds opt-in `orthogonal-four-resource-renewal-v2`, which reuses the existing unnamed wave vectors, periods, phases and amplitudes as a continuously moving abiotic target. Positive and negative renewal fluxes are recorded separately and enter an explicit open-system resource ledger. No resource roles, diversity reward, lineage protection or population feedback are added.

v0.56 also fixes the repeated `conda-sync` version mismatch. The cause was timestamp-based stale Python bytecode: same-length version edits made within a preserved one-second mtime window could leave an old `se.__version__` executable even while `se.__file__` pointed to current source. `conda-sync` and editable verification now clear project bytecode before importing the package, and a regression test reproduces the exact collision.

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

## Run D3-D

```bash
se-d3-resource-renewal \
  --config configs/mvp_short_d3d_persistent_resource_renewal_longrun.json \
  --seeds 56001,56002,56003 \
  --output analyses/d3d_persistent_resource_renewal_1500 \
  --backend gpu \
  --until-tick 1500
```

D3-D establishes persistent external opportunity axes. It is not evidence for migration, collection-processing specialization, coexistence, trophic differentiation or named resource roles.

## Current version documents

- [D3-C result interpretation](docs/v0.56/D3C_RESULT_INTERPRETATION.md)
- [D3-D design](docs/v0.56/D3D_PERSISTENT_RESOURCE_RENEWAL_DESIGN.md)
- [D3-D run plan](docs/v0.56/D3D_PERSISTENT_RESOURCE_RENEWAL_PLAN.md)
- [Paired renewal mechanism report](docs/v0.56/D3D_RENEWAL_MECHANISM_REPORT.md)
