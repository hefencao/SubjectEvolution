# D2-J compositional embodied module design

## Purpose

D2-J tests whether the already-used v2 hierarchy can span more than one embodied consequence. It is a substrate extension, not a claim that a niche, organ, or social role has evolved.

## Versioned schema

- module schema: `expression-gated-compositional-embodied-v3`
- input schema: `internal-needs-local-resources-feedforward-v2`
- output schema: `harvest-locomotion-signal-repair-v1`
- coupling schema: `lower-slot-signal-modulation-v1`

Each of four fixed modules retains its gate, ten contextual inputs, bias, and four harvest-router genes. Three additional inherited router genes publish the same module signal to:

1. `locomotion_power`
2. `signal_power`
3. `repair_drive`

The six lower-slot-to-higher-slot coupling genes remain unchanged. A weak upstream module can therefore alter a strong downstream module that publishes to any mixture of the seven output coordinates.

## Physical semantics

### Locomotion power

The bounded signed output scales the speed of existing successful movement actions. Movement energy scales with the square of the applied speed multiplier. It does not select an action or create displacement without an existing movement action.

### Field-signal power

The bounded signed output scales the strength of existing resource, danger, and social field emissions. Signal energy scales quadratically with the multiplier. Direct-message payload content is unchanged.

### Repair drive

Only positive drive requests repair. Material and energy are debited before integrity is restored. Repair is capped by available material, available energy, and missing integrity. Negative output suppresses this primitive rather than creating a damage actuator.

## Cost and ablation

Every embodied router weight pays explicit maintenance and development energy. `neutralize-functional-module-embodied-output` sets all three effective outputs to zero while preserving:

- v3 genes and mutation;
- expression and coupling;
- direct harvest output;
- coupling cost;
- embodied-router structure cost.

This separates output use from free deletion or cost refund.

## Diagnostic boundary

D2-J reports both the three-port embodied effective dimension and the combined seven-coordinate output-basis effective dimension. A larger diagnostic dimension is not itself an ecological niche. Ecological claims still require environment association, persistence, coexistence, and removal/counterfactual evidence.

## Known limits

The graph remains four-slot, fixed, and acyclic. The output vocabulary is versioned and finite. D2-J does not implement dynamic topology, arbitrary output routing, new sensors, physical morphology, module duplication, or diversity protection.
