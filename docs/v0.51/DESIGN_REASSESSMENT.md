# v0.51 design reassessment

## Why v0.50 was not the recommended next run

The v0.50 opt-in v4 layer correctly moved locomotion, signalling and repair below the functional-module boundary, but it still represented the body with four coarse drives and three bounded condition variables. That was useful as a compatibility-preserving prototype, not yet a sufficiently articulated causal substrate for continued long runs.

The supplied design discussion was therefore treated as a design review, not copied wholesale.

## Retained

1. **Generic functional operators.** Modules remain fixed, bounded computation units with inherited input selection, transformation, expression, routing and feed-forward composition. No module is named as an organ or ecological role.
2. **Layered causal generation.** Genotype produces inherited physiological parameters; functional modules read environment and body state and publish regulatory intent; body dynamics convert intent into actual execution under material and energy constraints.
3. **Intent/execution separation.** A module cannot directly create oxygen, a messenger, repair or locomotor performance. It can only stimulate a bounded process whose realized rate is limited by inherited capacity, current state and available substrate.
4. **Fixed lifetime weights.** No online Hebbian or gradient update is introduced. History is represented by explicit bounded states with deterministic decay and accumulation.
5. **Costed computation.** Actual module activation and inherited route load debit energy and oxygen.
6. **Counterfactual access.** Regulatory output can be neutralized, messenger receptors can be blocked and bounded physiology states can be clamped without changing genotype or random streams.

## Modified

### Expression gates are retained

The discussion proposed removing static expression gates because lateral inhibition can also silence a module. The project charter, existing genotype ABI and previous causal audits require structure, expression, use and cost to remain separable. v0.51 therefore retains the inherited expression gate while dynamic context, body state and feed-forward signals determine actual activation.

### Sparse routing remains continuous but costed

Gumbel-Softmax and annealed training are not appropriate in the current deterministic evolutionary kernel. Input/output and coupling routes remain continuous bounded genes. Their magnitude contributes to structural and computation cost, and all routes are directly inspectable and ablatable. A future version may add a deterministic inherited K-hot routing schema as a separate ABI rather than changing v1-v5 semantics in place.

### ODE language becomes fixed discrete-time fluxes

The runtime uses one deterministic bounded update per simulation tick rather than a general-purpose ODE solver. Every flux has an explicit source, sink, capacity and clamp. This preserves seed replay, CPU/GPU parity boundaries and checkpoint transparency.

### Named hormones are replaced by abstract messenger buses

The system does not hard-code adrenaline, cortisol or oxytocin. It provides two abstract decaying whole-body buses:

- **mobilization messenger** — can raise movement and signal execution while increasing oxygen demand;
- **maintenance messenger** — can improve fatigue clearance and repair while reducing immediate movement capacity.

The two buses have independently inherited synthesis, decay and receptor parameters but compete for one finite precursor pool. Ecological conditions may later recruit them into different evolved roles.

## Deferred or rejected for this stage

- online Hebbian or gradient learning;
- arbitrary recurrent operator graphs;
- Gumbel/Concrete training machinery;
- module duplication/deletion;
- named organs, named hormones or preset ecological roles;
- multicellular morphogen and cell-type systems;
- unconstrained dynamic code or arbitrary action-port creation.

These are not declared impossible. They are deferred until the fixed physiological and ecological substrate has generated interpretable stable structures.

## v0.51 causal boundary

```text
fixed inherited functional operators
        ↓ regulatory requests
oxygen uptake modulation | mobilization stimulation
maintenance stimulation  | sensory attention modulation
        ↓
inherited transport / reserve / conversion / power / transduction
independent messenger synthesis / decay / receptor gains
shared finite precursor + energy + oxygen + material
        ↓
oxygenation, fatigue, tissue, structure, messenger states
        ↓
actual movement, sensing, signalling, repair and damage
```

Zero regulatory output means basal oxygen uptake and basal attention, with no stimulated messenger synthesis. This is intentionally different from archived v4, where a zero coarse drive mapped to the middle of a normalized drive range.
