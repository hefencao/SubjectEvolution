# D2-L conservative regulatory physiology

## Problem found in the v0.51 run

The supplied 1500-tick result contains negative cumulative values for messenger synthesis, precursor use and messenger synthesis energy in all three seeds. These fields are flow magnitudes, so negative values are not a biological outcome. They reveal a runtime conservation error.

The legacy limiter accepted a negative current energy value as a synthesis budget. Dividing that negative budget by a positive per-unit cost produced a negative scaling factor, converting a positive synthesis request into negative synthesis. Later zero-clamping could also erase the energy debt before the world starvation settlement.

## Versioned correction

### Legacy replay

`transport-metabolism-messenger-tissue-v2` is unchanged and remains loadable. It exists only so v0.51 checkpoints and results can be reproduced exactly.

### Conservative runtime

`transport-metabolism-messenger-tissue-v3` changes only settlement semantics:

1. Regulatory synthesis requests and spending limits are constrained to non-negative values.
2. Synthesis is limited by non-negative available precursor and energy.
3. Precursor recovery is limited by non-negative available material.
4. Repair is limited by non-negative available material, energy and oxygen.
5. Computation cost is always debited because computation has already occurred.
6. Negative energy is preserved until the existing world starvation settlement converts it into integrity damage.
7. Every reported per-tick physiology flow is checked for finiteness and non-negativity before it is accumulated.

## Scope

The correction does not add a new function, module, organ, hormone, ecological role or diversity mechanism. The inherited fifteen-parameter physiology, two abstract messenger buses, fixed operator kernel, bounded states and existing counterfactual interfaces remain unchanged.

The original D2-L result cannot be interpreted as long-run evidence for messenger or precursor dynamics. The same seeds must be rerun under v3 before those flows are used scientifically.
