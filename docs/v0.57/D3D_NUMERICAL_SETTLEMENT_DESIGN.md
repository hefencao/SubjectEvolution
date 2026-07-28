# D3-D numerical settlement design

## Constraint

Physical source, sink, residue release, admitted harvest and final inventory must remain separately interpretable. Numerical settlement must not be hidden inside any physical term and must not feed simulation state.

## Recorded quantities

### Field-update settlement

For each channel and tick:

```text
actual inventory after release/renewal/diffusion/clipping
- inventory before update
- residue released
- renewal source
+ renewal sink
```

### Harvest-commit settlement

For each channel and tick:

```text
actual inventory removed by the float32 field commit
- admitted harvested amount
```

The terms are accumulated in `float64` diagnostics. They are initialized only for persistent renewal, synchronized across CPU/device/checkpoint paths, and are absent from older schemas.

## Ledger reports

D3-D results v2 report:

- `unadjusted_residual`;
- `field_roundoff`;
- `harvest_roundoff`;
- `numerical_adjustment`;
- corrected `residual`;
- unadjusted and corrected relative errors;
- numerical-adjustment fraction of total ledger scale;
- validity of the corrected identity.

Missing v1 fields are read as zero for compatibility. This preserves the original failed result instead of retroactively changing its meaning.

## Scientific boundary

The settlement terms are implementation provenance. They are not:

- environmental sources or sinks;
- recycling;
- entity waste;
- fitness costs;
- diversity maintenance;
- rescue mechanisms;
- ecological roles.

No field value is corrected after the fact. The simulator continues to use its original authoritative float32 state.
