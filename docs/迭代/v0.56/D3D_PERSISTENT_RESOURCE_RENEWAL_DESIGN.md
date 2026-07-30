# D3-D persistent role-free resource renewal

## Problem

The v1 orthogonal resource schema does not maintain the configured four-channel spatial opportunity structure. Its long-run regeneration equilibrium is uniform carrying capacity, so shared entity demand can synchronize channel fields even when initialization is orthogonal.

## Opt-in contract

D3-D adds `orthogonal-four-resource-renewal-v2`. Tick zero is byte-for-byte compatible at the mathematical field level with the existing orthogonal initial pattern. Later ticks reinterpret the existing channel wave vectors, periods, phases and amplitudes as a moving abiotic renewal target.

For each channel and cell:

```text
delta = regeneration_rate * (moving_target - current_resource)
source = max(delta, 0)
sink   = max(-delta, 0)
```

Source and sink are recorded separately. Diffusion, conservative pre-harvest intake, delayed conversion and D3-C external recycling remain unchanged.

## Causal and scientific boundaries

- No entity, lineage or group state feeds back into the renewal target.
- All four channels use the same equation and remain unnamed.
- No diversity reward, population rescue, carrying-capacity adjustment or role protection is added.
- The world is explicitly open with respect to abiotic source and sink fluxes; both are present in the external resource ledger.
- D3-D tests persistent external opportunity, not migration, coexistence, collection-processing specialization or trophic differentiation.

## Ledger

```text
initial external resource
+ abiotic renewal source
+ residue release
= harvested resource
+ abiotic renewal sink
+ final external resource
```

Diffusion is internal spatial transfer and therefore cancels globally.
