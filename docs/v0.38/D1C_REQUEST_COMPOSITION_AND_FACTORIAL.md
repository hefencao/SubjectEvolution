# D1-C explicit request composition and paired factorial experiments

## Problem found in the v0.37 long run

The v0.37 report showed that the resource field retained more dimensions and
that all four elastic capacities were actively used. However, its harvest panel
used realized extraction volume. All four realized channels rise and fall with
population size and total HARVEST actions, so a near-one raw temporal dimension
cannot distinguish synchronized demand from common scale.

## Request versus realization

v0.38 adds a separate authoritative accounting path:

- `requested_harvest_resources_window`: intent before resource availability and
  competing requests are resolved;
- `harvested_resources_window`: actual amount committed after resolution;
- `harvest_extraction_efficiency_window`: realized total / requested total.

The long-run analyzer reports raw volumes and normalized per-window shares for
both request and realization. Explicit request fields are authoritative. Legacy
uniform allocation can be reconstructed from action count and fixed channel
rates; legacy selective allocation cannot and is marked unavailable.

## D1 affinity × capacity factorial

Branches:

| Branch | Affinity expression | Capacity expression |
|---|---|---|
| baseline | inherited | inherited |
| affinity-neutral | neutral midpoint | inherited |
| capacity-neutral | inherited | neutral midpoint |
| combined-neutral | neutral midpoint | neutral midpoint |

All branches start from the same trusted checkpoint and preserve genotype and
keyed randomness. Effects are expressed phenotype minus its neutralized paired
branch. The interaction contrast is:

```text
baseline - affinity-neutral - capacity-neutral + combined-neutral
```

The experiment is phase-local and horizon-local. It does not establish that a
phenotype is universally beneficial or that a higher-level subject exists.

## Smoke boundary

The included short smoke verifies branch execution and contrast accounting. Its
small population, short horizon and single source run are integration evidence
only. The full v0.37 source result is not embedded in the source package; the
compact summary is retained and the raw result belongs in the validation bundle.
