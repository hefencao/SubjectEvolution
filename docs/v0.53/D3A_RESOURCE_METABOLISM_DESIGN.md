# D3-A inherited resource buffering and delayed conversion

## Problem

The existing four-channel environment is externally orthogonal, but successful harvest is immediately converted by the resource-effect matrix into body outcomes. This makes acquisition and conversion inseparable and strongly favors short-horizon energy collection.

## Conservative extension

Each entity receives four bounded raw-resource stores. Store capacity and per-tick conversion capacity are inherited independently per channel. Base values are identical across channels. No channel is named as food, oxygen, mineral, toxin, or reproductive material.

Tick order is fixed:

1. Convert and decay raw material that was already stored before the tick.
2. Build observations, including normalized store occupancy.
3. Select and resolve actions.
4. Assimilate successful harvest into bounded stores.
5. Record overflow and any stored material lost with dead carriers.

New harvest therefore cannot affect body state until at least the next tick. Converted material uses the existing versioned resource-effect matrix; D3-A does not add a second hand-written effect vocabulary.

## Genetics

The physiology genome adds eight bounded parameters:

- `resource_store_capacity_0..3`;
- `resource_conversion_capacity_0..3`.

They mutate and inherit through the existing deterministic genome path. The functional genome is unchanged except that its input selector can read four normalized store-occupancy channels.

## Conservation boundary

For every channel:

```text
stored = converted + decay + death loss + final living store
```

Overflow is material rejected before entering the internal store and is reported separately. Current death loss is explicit dissipation, not hidden recycling. A detritus pool is deferred because it requires a separately conserved external transfer process.

## Claims deliberately not made

D3-A does not establish metabolism classes, migration, trophic roles, coexistence, ecological differentiation, or module maturity. Its purpose is to remove the immediate-reward collapse and create an inherited temporal processing axis for later ecology.
