# D3-E costed spatial processing design

## Evidence gate

The supplied D3-D v2 panel closes both external ledgers in all three 1500-tick seeds and retains multiple effective resource dimensions. That supports adding a bounded processing-opportunity substrate. It does not itself support migration or specialization.

## Mechanism

`phase-shifted-channel-processing-support-v1` reuses each unnamed resource channel's existing persistent-renewal wave vectors, periods, phases, and amplitudes. Both wave components are advanced by one quarter cycle. The resulting bounded fraction is centered around one and scaled by `resource_processing_support_amplitude`.

The support field:

- adds no matter;
- observes no entity, lineage, group, population, or diversity state;
- does not change policy logits, actions, harvest requests, or resource identity;
- affects only the amount converted from internal raw stores during the pre-observation metabolism step.

For entity `i` and channel `c`:

```text
requested = min(store, inherited conversion capacity)
supported = min(store, inherited conversion capacity × local support)
```

## Cost and energy arbitration

Every supported conversion unit requests `resource_processing_energy_per_unit[c]`. If total requested execution energy exceeds current energy, every channel's supported amount is multiplied by the same entity-level factor. This avoids a channel-order priority. Energy is debited before the existing resource-effect matrix realizes body outcomes.

The raw-store ledger remains:

```text
store before = converted + decay + store after
```

Execution energy is a separate body-energy flow, not a resource source or sink.

## Ablation

`neutralize-spatial-processing-support` fixes the effective multiplier at `1.0` and preserves:

- per-unit processing energy costs;
- inherited store and conversion genes;
- resource fields and renewal dynamics;
- genotype and inheritance;
- random streams and checkpoint state.

## Paired experiment

For every seed, `se-d3-spatial-processing` writes a full-world checkpoint at tick 0 and restores two branches:

- `spatial-support`: configured heterogeneous support;
- `neutral-support`: multiplier `1.0` through the intervention.

The experiment reports the checkpoint state hash for both branches and refuses to continue if either branch differs from the source hash.

## Interpretation boundary

The experiment can attribute paired branch differences to support neutralization under the shared-checkpoint contract. It cannot establish a general fitness effect from a small seed panel, and it cannot establish migration, specialization, coexistence, trophic transfer, or named ecological roles.
