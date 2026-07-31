# D1-J inherited fixed-budget resource storage

## Charter role

D1-I establishes a real fixed conversion-rate opportunity cost, but inherited
allocations remain close to the neutral four-channel vector and demographic
direction is not repeated. The four storage genes still allow all channels to
expand independently, so internal material capacity lacks a conserved volume
tradeoff.

D1-J assigns those existing four storage genes to one fixed total internal
storage volume. Increasing capacity for one raw resource necessarily reduces
capacity available to the others. No reward, resource field, conversion matrix,
action, or role label is changed.

## Capability contract

The physiology retains the same eight resource-metabolism genes. Four storage
genes become positive weights over the configured total storage volume; four
conversion genes retain D1-I fixed-total allocation semantics. Every entity must
satisfy:

```text
sum(resource_store_capacity[channel])
== sum(configured resource_store_base_capacity)
```

Maintenance and development costs depend on the fixed total, not allocation
direction. Existing store contents are never truncated when an intervention or
mutation changes expressed capacity; capacity only constrains future intake.

## Cost-preserving neutralization

`neutralize-resource-store-allocation` replaces only expressed store capacities
with the configured neutral channel-base vector. It preserves genotype, current
stores, conversion allocation, total storage volume, physiology costs, resource
fields, random keys, and future-offspring neutralization.

## Calibration boundary

The first three-seed panel uses exact tick-480 shared checkpoints and a 120-tick
paired horizon. It verifies storage-budget closure, non-neutral inherited
allocation, current-store preservation, conversion preservation, and observable
resource/body consequences. It has no pass/fail gate and authorizes no
ecological, coexistence, adaptive, or selection claim.
