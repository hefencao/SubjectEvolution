# SE v0.59

SE is a deterministic artificial-life and subject-structure research platform. The current main line combines conservative regulatory physiology, inherited delayed resource processing, storage-constrained intake, identity-preserving external raw-material recycling, persistent four-channel abiotic renewal, costed spatial processing support, and a read-only shared-checkpoint response audit.

## Why v0.59

The supplied D3-E panel completed three shared tick-0 checkpoint pairs to tick 1500. Every active branch experienced both support-limited and support-accelerated conversion, every branch paid processing cost, and both external ledgers closed. Active-minus-neutral conversion was negative in all three seeds, while endpoint survival differences had mixed signs. This retains the substrate but does not establish migration, specialization, coexistence, trophic transfer, or ecological roles.

D3-F therefore adds measurement and counterfactual orientation control rather than another ecological mechanism:

- `reverse-spatial-processing-support` rotates only the non-material support surface by 180 degrees;
- resource fields, residue, renewal targets, genotype, inheritance, random state, and per-unit processing cost are preserved;
- original, reversed, and neutral branches restore the same tick-0 full-world checkpoint;
- a read-only observer records inventory-weighted exposure, support gain relative to staying in place, movement-gradient alignment, and store-support occupancy correlation;
- no processing-support sensor, movement reward, migration controller, diversity protection, or role label is added.

Finite-seed response signs remain observations. D3-F is a prerequisite audit for later migration experiments, not a migration or ecotype result.

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

## Run D3-F

```bash
se-d3-processing-response \
  --config configs/mvp_short_d3e_spatial_processing_longrun.json \
  --seeds 59001,59002,59003 \
  --output analyses/d3f_processing_response_1500 \
  --backend gpu \
  --until-tick 1500 \
  --observation-period 30
```

Each seed produces original-support, reversed-support, and neutral-support branches from one shared tick-0 checkpoint.

## Current version documents

- [D3-F design](docs/v0.59/D3F_PROCESSING_RESPONSE_AUDIT_DESIGN.md)
- [Supplied D3-E result](docs/v0.59/D3E_SUPPLIED_RESULTS.md)
- [Implementation report](docs/v0.59/IMPLEMENTATION_REPORT.md)
