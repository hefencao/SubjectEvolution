## D4-A resource-geography × inherited-affinity boundary

```text
shared redesigned-source checkpoint
├── baseline
├── resource geography reversed 180°
├── inherited affinity expression neutralized
└── both interventions

interaction
= (baseline − resource-reversed)
  − (affinity-neutral − joint-neutral)
```

The resource-only reversal rotates the current four-channel resource fields and
the future seasonal regeneration template. It does not rotate hazard or
mortality trace, relabel resource channels, change the resource effect matrix,
move entities, edit genotype, or alter lineage membership. The affinity
neutralization preserves genotype and only replaces the expressed affinity with
the fixed uniform vector.

All checkpoint branches reuse the same keyed random streams. Each planned
lineage is summarized in every branch, but independent panel seeds—not lineages
or outcomes—are the replication unit. The pre-intervention exposure diagnostic
compares affinity-weighted utility under original and rotated resource fields;
it is structural provenance, not an additional intervention.

A repeated interaction authorizes a longer environment-matching confirmation
only when the interaction is also aligned with material preregistered source
exposure and spans multiple dominant affinity channels. The supplied v0.47 run
fails that alignment gate. Even an eligible interaction cannot by itself
establish stable ecological niches, because coexistence, removal and map-scale
tests remain outstanding.

# SE architecture

## D2-E confirmation-selection boundary

```text
120-tick lineage-pair results
        ↓
practical thresholds applied separately to
output routing / retained cost / total expression
        ↓
same material output direction in
≥2 seeds and ≥2 non-dominant lineage identities
        ↓
module-level continuation decision
        ↓
300-tick plan preserves every original pair
```

Individual checkpoint-lineage pairs are never selected for confirmation by their observed response. A module may pass the 120-tick screen, but its confirmation plan retains dominant and non-dominant pairs from all original checkpoint conditions. Cost-refund and total-expression signals cannot substitute for routed-output evidence.

## D2-D lineage-conditioned experiment boundary

```text
shared checkpoint + pre-intervention lineage census
├── baseline: output + expression cost
├── target lineage output-neutral: no routed residual, cost retained
└── target lineage expression-neutral: no routed residual, no cost

paired decomposition
├── output effect = baseline − output-neutral
├── retained-cost effect = output-neutral − expression-neutral
└── total effect = baseline − expression-neutral
```

The target is a genetic lineage ID already present at the checkpoint. Selection
uses membership only, not endpoint response. Treatment state belongs to the
experiment branch and follows same-lineage descendants; it does not alter genes,
lineage membership, entity IDs, reproduction, mutation, module topology or
world abundance. Equal lineage weighting occurs only in offline aggregation.
When no targeted intervention exists, the runtime passes no row mask and uses
the unchanged authoritative module path.

## D2-C evidence qualification boundary

```text
shared checkpoint
├── immediate full-expression preference/channel
├── immediate all-neutral preference/channel
├── immediate per-module-neutral preference/channel
└── top-lineage footprint summaries

120-tick paired endpoints
        +
300-tick paired endpoints
        ↓
outcome thresholds + seed/phase replication + lineage guard
        ↓
stop / refresh footprint / future copy-number candidate
```

Immediate footprint is evaluated before branch stepping and never feeds the
world. Endpoint contrasts remain separate from direct action-interface reach.
A module is not duplication-ready solely because a deterministic endpoint is
non-zero.

## D2-B contribution and intervention boundary

```text
authoritative D2-A module evaluation
├── unchanged summed raw output + final quantization → world
└── isolated per-module diagnostics → progress only

shared checkpoint
├── baseline
├── all modules neutral
├── module 0 neutral
├── module 1 neutral
├── module 2 neutral
└── module 3 neutral
```

Per-module diagnostic rounding and immediate-footprint evaluation never feed the authoritative preference. Partial
neutralization preserves genotype and removes only the selected module
expression and its proportional maintenance/development cost. Analysis and
experiments depend on runtime; runtime does not depend on the D2 audit.

## D2-I compositional module boundary

The archived v1 path remains four independent additive slots. The opt-in v2 path adds a fixed acyclic signal graph without adding world ports:

```text
module 0 signal ─┬─→ module 1 contextual activation
                 ├─→ module 2 contextual activation
                 └─→ module 3 contextual activation
module 1 signal ─┬─→ module 2 contextual activation
                 └─→ module 3 contextual activation
module 2 signal ───→ module 3 contextual activation

all four slots still publish bounded zero-sum harvest-request residuals
```

Six lower-triangular coupling genes are inherited and mutated. A weighted upstream signed signal multiplicatively scales a downstream slot's original contextual activation. The scale is bounded, the graph is feed-forward, and the existing authoritative sum-then-round output order is preserved.

`neutralize-functional-module-coupling-output` disables only the mediated signal graph. It does not remove direct module output, coupling genes, mutation or coupling structure cost. This makes a fresh-population active/neutral comparison a test of reachable composition rather than free gene deletion.

The v2 layer can express hierarchy and joint dependence among modules sharing the harvest port. It still cannot create new sensors, movement, conversion, storage, signalling or social-control functions. A failure after v2 coupling is actively used would therefore locate the next bottleneck at the primitive/output vocabulary rather than automatically at the environment.

## D2-A bounded module boundary

```text
fixed inherited module tensor
  ├─ expression gate
  ├─ ten fixed inputs
  │    bias + five body deficits + four local resources
  ├─ bounded transform weights
  └─ four-output router
            ↓
zero-sum harvest-request residual
            ↓
static inherited affinity + contextual residual
            ↓
keyed one-channel HARVEST request
```

Both v1 and v2 module layers cannot choose an action, alter resource assimilation,
modify resource-gradient utility, create a world field, or publish to movement,
signalling, sharing, memory or social control. The v1 path has no inter-module
signal; v2 adds only bounded feed-forward modulation among the same harvest
modules. This narrow boundary prevents a
second unrestricted policy network while testing expression-gated functional
routing.

`neutralize-functional-modules` preserves genotype and returns the effective
request weights to static affinity. Module maintenance and development costs are
charged only when expression is active.

## Request/realization boundary

```text
external resource fields
  └─ generated without entity, lineage or group feedback

HARVEST action + static affinity + optional D2 contextual residual
  └─ requested_harvest_resources[entity, channel]
       ├─ recorded before environment allocation
       └─ fixed total request budget

conflict/environment resolution
  └─ harvested_resources[entity, channel]
       ├─ limited by local availability and competing requests
       └─ committed to body and environment state
```

Requested resources are causal intents. Realized resources are constrained
outcomes and must not be substituted for requests.

## D1 factorial boundary

```text
shared trusted checkpoint
├── baseline
├── neutralize-resource-affinity
├── neutralize-elastic-capacities
└── neutralize both
```

An existing `d1_factorial_plan.json` can be reused with `--plan`, avoiding a new
observational phase-selection pass.

## Package layout

```text
se/
├── analysis/
├── cmd/
├── differentiation/
├── env/
├── evolution/
├── experiments/
├── gui/
├── knowledge/
├── runtime/
├── subjects/
└── cfg.py + shared infrastructure
```

## Dependency direction

```text
cfg / shared infrastructure
            ↓
env / differentiation / evolution / knowledge / subjects
            ↓
runtime
            ↓
cmd / gui

analysis / experiments → runtime + domains
runtime + domains ✕→ analysis / experiments / gui
```

## Local development boundary

The normal local runtime is an activated conda environment with one editable
installation of the current checkout. `make conda-sync` installs with
`--no-build-isolation`, then proves that `direct_url.json`, package imports,
metadata and all six console scripts refer to the exact checkout. Ordinary source
edits require no reinstall. `make conda-check` adds tests and an external smoke
with an empty `PYTHONPATH`.

Wheel/sdist validation remains a release-transfer audit and is not the local
runtime environment.

## Backends and GUI

- `cpu`: authoritative reference semantics.
- `gpu` + `strict-reference`: GPU availability validation with CPU-authoritative world.
- `gpu` + `hybrid-accelerated`: experimental accelerated stages; parity remains separate.
- `se.gui`: observation-only shared-frame publication.

## D2-J compositional embodied output boundary

The opt-in v3 layer retains the fixed four-slot feed-forward module graph and the archived harvest residual. Each slot adds three inherited router coordinates for locomotion power, field-signal power, and repair drive.

Locomotion and field-signal outputs modulate existing world interfaces and pay use costs. Repair explicitly debits material and energy before restoring integrity. The module layer still does not select an action, invent a sensor, assign an ecological role, or alter module copy number.

`neutralize-functional-module-embodied-output` removes only effective publication to the three embodied ports. Genes, mutation, expression, coupling, harvest routing, and embodied-router structural cost remain present. Combined output-basis diagnostics are observational and never feed policy or world state.

## v0.51-v0.52 regulatory physiology boundary

```text
fixed functional operators + expression + feed-forward coupling
        ↓ signed regulatory requests
basal oxygen-uptake modulation | mobilization stimulation
maintenance stimulation       | sensory-attention modulation
        ↓
fifteen inherited transport / reserve / conversion / power / transduction /
fatigue / repair / messenger parameters
        ×
finite energy + oxygen + material + shared messenger precursor
        ×
local oxygen + terrain resistance + mechanical wear
        ↓
oxygenation + fatigue + tissue + structure + two decaying messenger states
        ↓
actual movement, sensing, signalling, damage and repair
```

The functional layer emits intent only. The body layer settles realized fluxes. Two abstract messenger paths have independent inherited synthesis, decay and receptor gains but compete for a shared precursor. This provides global, decaying cross-module regulation without naming a hormone or organ.

Lifetime operator weights remain fixed. History is explicit bounded state, not hidden online parameter learning. Expression gates remain separate from use and cost because the project charter and prior causal audits require those boundaries to be independently observable.

Counterfactual branches can neutralize regulatory publication, block both messenger receptor paths, or clamp any bounded physiology state. These treatments are deterministic, checkpointed and do not modify genotype or randomness.

The v4 coarse-drive path remains an archived schema. With v5 disabled, v1-v4 execution is unchanged.

### v0.52 conservation correction

The legacy `transport-metabolism-messenger-tissue-v2` settlement is retained byte-for-byte for replay. New runs use `transport-metabolism-messenger-tissue-v3`, which enforces a finite non-negative per-tick flow ledger. Synthesis and repair spend only non-negative available substrate. Functional computation is still charged after it occurs; any resulting negative energy remains visible until the existing world starvation settlement converts debt into integrity loss. No new biological degree of freedom is introduced by this correction.

## v0.53 delayed raw-resource metabolism boundary

The D3-A opt-in path separates acquisition from body reward. Successful harvest is first assimilated into four bounded internal raw-resource stores. Only store content present before a tick may be converted during that tick, which guarantees a minimum one-tick delay between acquisition and body effect.

Storage and conversion capacities are inherited independently per channel. Base capacities, conversion rates, and decay rates are equal across channels; channel meaning remains defined only by the existing versioned resource-effect matrix. Functional operators receive normalized store occupancy as additional inputs but keep the same fixed four-slot topology and regulatory output vocabulary.

The authoritative raw-store ledger is `stored = converted + decay + death loss + final living store`. Overflow is reported separately because it never enters the body store. Stored material carried by dead entities is currently explicit dissipation; no detritus recycling is implied.
