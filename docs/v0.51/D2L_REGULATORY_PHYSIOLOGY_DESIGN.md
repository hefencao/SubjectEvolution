# D2-L inherited regulatory physiology

## Fixed inherited parameter set

v0.51 adds fifteen bounded genes after the functional-module genome:

1. oxygen transport capacity;
2. oxygen reserve capacity;
3. aerobic conversion efficiency;
4. anaerobic tolerance;
5. mechanical power capacity;
6. information transduction capacity;
7. fatigue clearance capacity;
8. repair conversion efficiency;
9. structure repair allocation;
10. mobilization-messenger synthesis capacity;
11. maintenance-messenger synthesis capacity;
12. mobilization-messenger decay capacity;
13. maintenance-messenger decay capacity;
14. mobilization-messenger receptor gain;
15. maintenance-messenger receptor gain.

The two messenger pathways can therefore diverge independently while sharing a finite precursor pool. The shared pool creates a physical tradeoff rather than an explicit diversity objective.

## Dynamic states

All states are bounded and checkpointed:

- oxygenation;
- tissue condition;
- structure condition;
- metabolic fatigue;
- mobilization messenger;
- maintenance messenger;
- messenger precursor;
- next-tick physiological sensor multiplier.

## Module requests

The four auxiliary module outputs are signed regulatory values:

- oxygen-uptake modulation: zero is basal uptake, positive raises and negative suppresses uptake;
- mobilization stimulation: only positive output stimulates synthesis;
- maintenance stimulation: only positive output stimulates synthesis;
- sensory-attention modulation: zero is basal attention, positive raises and negative suppresses attention.

Neutralizing module physiology output therefore produces a true basal body, not a half-strength request.

## Conserved fluxes

- Messenger synthesis consumes precursor and energy.
- Precursor recovery consumes material.
- Module computation consumes energy and oxygen according to actual signal and inherited route load.
- Movement and field signalling consume oxygen according to realized body performance.
- Fatigue accumulates from work, computation and oxygen shortfall and clears according to oxygen, maintenance signalling and inherited capacity.
- Repair consumes material, energy and oxygen and is allocated between tissue and structure by an inherited parameter.

## Counterfactual interfaces

- `neutralize-functional-module-physiology-output`
- `block-physiology-messenger-receptors`
- `Simulation.set_physiology_state_clamp(name, value)`
- `Simulation.clear_physiology_state_clamps()`

All are deterministic, checkpointed and clone-safe. They modify no genotype coordinate and consume no random draw.

## Interpretation boundary

D2-L establishes a better causal substrate. It does not establish organs, hormones, ecological niches, trophic levels or stable coexistence. It also does not justify changing module copy number.
