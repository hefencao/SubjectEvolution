# D1-I inherited fixed-budget resource conversion

## Charter role

D1-H successfully couples current conservative-store room to inherited sensing,
but all three paired panels are demographically identical and nearly energy
neutral. About 3.6 of four stores remain open per entity, so current demand is
still close to a common all-channel shortage signal.

D1-I introduces an internal opportunity cost before adding more sensing or
environment amplitude. The existing four conversion-capacity genes allocate one
fixed total conversion budget across resource channels. Increasing one channel
therefore reduces capacity available to others.

## Capability contract

The physiology keeps the same eight resource-metabolism genes and the same
configured total conversion capacity. Four storage genes retain their previous
bounded-capacity semantics. Four conversion genes become positive allocation
weights over the fixed total:

```text
sum(resource_conversion_capacity[channel])
== sum(configured resource_conversion_per_tick)
```

The allocation is inherited and mutable. Existing physiology maintenance and
development costs depend on total capacity, not allocation direction. The
world resource-effect matrix, stores, harvest rules, action vocabulary, sensing
schema, and environment remain unchanged.

## Cost-preserving neutralization

`neutralize-resource-conversion-allocation` replaces only the expressed channel
allocation with the configured neutral channel-base vector. It preserves
conversion total, genotype, stores, physiology costs, resource fields, random
keys, and future offspring neutralization.

## Calibration boundary

The first three-seed panel uses exact tick-480 shared checkpoints and a 120-tick
paired horizon. It verifies total-budget closure, non-neutral inherited
allocation, cost preservation, and non-degenerate store/body consequences. It
has no pass/fail gate and authorizes no ecological, coexistence, adaptive, or
selection claim.
