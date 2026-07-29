# SE v0.61

SE is a deterministic artificial-life and subject-structure research platform. The current main line keeps four role-free resource channels, conservative delayed storage and processing, identity-preserving external recycling, persistent abiotic renewal, costed spatial processing support, and shared-checkpoint response measurement.

## Why v0.61

The supplied D3-G runs completed the base, 1.5× linear, and 2× linear checkpoint panels. The larger scales each produced 12 population-supported acute panels, while the base scale produced none. No checkpoint met the evolutionary turnover gate.

Two measurement problems remained:

1. Short checkpoint-relative recycling ledgers did not record float32 settlement from residue-field diffusion/release and sparse residue deposits. The unrecorded term grows with field size and caused some otherwise conservative acute branches to be marked invalid.
2. The v1 panel had original active, reversed active, and original-orientation neutral branches. It did not have a reversed-orientation neutral branch, so the reversed active effect lacked a matched observation-orientation control.

v0.61 fixes both boundaries without adding a sensor, reward, migration controller, ecological role, population rescue, or diversity protection.

## D3-H matched acute response panel

`se-d3-processing-response-panel` now uses four branches from every predeclared checkpoint:

- `original-support`;
- `neutral-support`;
- `reversed-support`;
- `reversed-neutral-support`.

The matched causal contrasts are:

```text
original support effect = original-support - neutral-support
reversed support effect = reversed-support - reversed-neutral-support
```

Both neutral branches retain processing cost, genotype, resources, residue, checkpoint state, policy, and RNG state. The second neutral branch differs only in the support surface used by the read-only response observer.

The result separately records residue field-roundoff and sparse-deposit roundoff. Physical deposition, release, and final residue remain unchanged and visible.

## Cross-scale audit

`se-d3-response-scale-audit` reads one or more D3-G panel result files. It treats seed as the independent replication unit and checkpoints as nested repeated panels. Legacy three-arm v1 results remain readable, but their reversed-support effect is explicitly marked unidentified.

```bash
se-d3-response-scale-audit \
  --result base=analyses/d3g_response_panel_base/d3_processing_response_panel_results.json \
  --result scale1p5=analyses/d3g_response_panel_1p5/d3_processing_response_panel_results.json \
  --result scale2=analyses/d3g_response_panel_2/d3_processing_response_panel_results.json \
  --output analyses/d3g_scale_audit
```

## Run the v2 matched panel

```bash
se-d3-processing-response-panel \
  --config configs/mvp_short_d3g_spatial_processing_scale1p5_longrun.json \
  --seeds 61001,61002,61003 \
  --output analyses/d3h_response_panel_1p5 \
  --checkpoint-ticks 300,600,900,1200 \
  --response-window 120 \
  --observation-period 30 \
  --backend gpu
```

The 2× scale config can be used as an independent scale replication. Checkpoints within one seed are not independent seeds.

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

## Current version documents

- [Supplied cross-scale audit](docs/v0.61/D3G_SUPPLIED_SCALE_AUDIT.md)
- [Matched-control design](docs/v0.61/D3H_MATCHED_CONTROL_DESIGN.md)
- [Implementation report](docs/v0.61/IMPLEMENTATION_REPORT.md)
