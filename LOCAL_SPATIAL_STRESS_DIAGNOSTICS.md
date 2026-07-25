# Local Spatial Stress Diagnostics (v0.19.0)

## Purpose

The heterogeneous environment can keep global population nearly stable while local regions experience strong scarcity, crowding, hazard and mortality differences. `spatial-local-stress-diagnostics-v1` adds an observational analysis grid without changing policy, environment, groups, knowledge, reproduction or arbitration.

## Window accounting

For each configured analysis region the tracker accumulates:

- current population and population change;
- entity-tick exposure;
- births and deaths;
- mortality and birth pressure;
- mean occupied-position hazard;
- mean four-resource scarcity;
- mean same-cell crowding;
- owner-region benefit flow split into internal, cross-boundary and unbounded classes;
- boundary coverage, cohesion and outgoing retention.

The authoritative world remains the existing physical grid and dynamic entity/knowledge SoA. The analysis grid is not an ecological compartment, movement barrier, group label, knowledge capacity or reward.

## Configuration

```json
{
  "run": {
    "long_run_diagnostics_enabled": true,
    "long_run_diagnostics_schema": "long-run-evolution-diagnostics-v1",
    "spatial_stress_diagnostics_enabled": true,
    "spatial_stress_diagnostics_schema": "spatial-local-stress-diagnostics-v1",
    "spatial_stress_regions_x": 4,
    "spatial_stress_regions_y": 4
  }
}
```

The feature is disabled by default. When disabled, v0.18 evolution-progress and world semantics remain unchanged.

## Timing semantics

Population/environment exposure is sampled once per tick after field update and observation preparation. Births and deaths are attributed at their committed physical positions. Benefit energy is attributed to the owner's current analysis region. The tracker is checkpointed and cloned so window accounting survives exact continuation.

## Long-run analysis v4

`multi-seed-long-run-analysis-v4` adds a local region-window panel with:

- raw pooled correlations;
- within-region demeaned correlations;
- within-window demeaned correlations;
- first-difference correlations;
- same-region next-window correlations;
- spatial CV and local/global mortality ratios.

All results remain observational. Fixed-effect-style demeaning and differencing reduce some confounding but do not identify causality.

## Numerical fix

v0.19 also clamps tiny negative entropy values to zero before the NMI square-root denominator. This prevents a small-sample diagnostic-only complex-number failure observed in knowledge root/group alignment.
