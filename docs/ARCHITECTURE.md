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
metadata and the complete configured console-entry table refer to the exact checkout. Ordinary source
edits require no reinstall. `make conda-check` adds tests and an external smoke
with an empty `PYTHONPATH`.

Wheel/sdist validation remains a release-transfer audit and is not the local
runtime environment.

## Backends and GUI

- `auto` is the high-level default: use `gpu-hybrid-accelerated` when CUDA/CuPy is usable, otherwise record `cpu-fallback-no-gpu` and continue on CPU.
- `cpu` selects the authoritative reference implementation directly.
- `gpu` follows the same GPU-first/fallback policy as `auto`; the low-level `resolve_backend("gpu")` API remains strict for device-only validation.
- `strict-reference` is an explicit historical diagnostic with CPU-authoritative world semantics, not the production default.
- `hybrid-accelerated` keeps the CPU reference model as the semantic specification while executing registered stages on persistent device state.
- `tests/test_parity.py` is the authoritative cross-backend validation boundary and compares stage outputs, device mirrors and all checkpoint-authoritative state.
- `se.gui` remains observation-only shared-frame publication.

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

## D3-C external residual-material boundary

Resource-v6 adds a conditional four-channel field owned by the environment. The field exists only for the explicit recycling schema, so older environment objects and checkpoint state remain unchanged.

The authoritative sequence is:

1. release and diffuse residue already present at tick start;
2. update ordinary environmental resource regeneration;
3. deposit current-tick internal-store decay after the environment update;
4. deposit death-carried raw stores at the death cell;
5. release those deposits no earlier than the next tick.

All transfers preserve resource-channel identity. Release is limited by external field capacity; unreleased material remains in the residual field. No policy or entity controller writes directly to the field.

## v0.57 D3-D numerical settlement boundary

The D3-D physical mechanism remains the v0.56 moving-target source/sink contract. v0.57 changes only authoritative measurement.

```text
tick-start external inventory
+ residue release
+ abiotic source
- abiotic sink
        ↓ float32 field update, diffusion and clipping
actual pre-harvest inventory
- admitted harvest
        ↓ float32 segmented commit
actual final inventory
```

Two signed diagnostics close the boundary:

```text
field settlement
= actual pre-harvest inventory
  - (tick-start + release + source - sink)

harvest settlement
= actual field removal - admitted harvest
```

Therefore:

```text
initial + source + release + field settlement
= harvest + sink + final + harvest settlement
```

Both terms are numerical provenance, not biological fluxes, abiotic processes, rewards or correction forces. They never feed policy, ecology, field state, fitness, reproduction or renewal. The unadjusted physical-flux residual remains reported so numerical scale is auditable. Old v1 result files remain assessable with absent settlement terms interpreted as zero, but cannot retroactively prove closure.


## v0.58 D3-E spatial processing boundary

D3-E keeps acquisition, storage, processing support, processing execution, and body realization separate:

```text
external channel field
→ admitted harvest
→ bounded internal raw store
→ inherited conversion capacity × local abiotic support
→ explicit processing-energy arbitration
→ existing channel-to-body effect matrix
```

The support field is generated analytically from the role-free persistent-renewal wave basis with a quarter-cycle phase shift. It contains no entity feedback and no material inventory. It is queried at current entity cells before observation, after which ordinary entity-state synchronization publishes the realized store/body changes to the device mirror.

The support-neutralization intervention changes only the effective multiplier. It retains cost, genotype, resource fields, random state, and all other simulation mechanisms. The D3-E experiment obtains both branches by restoring one tick-0 checkpoint rather than constructing statistically similar initial states.

## v0.59 D3-F processing-response audit boundary

D3-F does not add an organism capability. It adds one support-only counterfactual and one read-only observer around the existing D3-E substrate.

```text
one tick-0 full-world checkpoint
        ├─ original non-material processing-support orientation
        ├─ 180° reversed non-material processing-support orientation
        └─ neutral multiplier 1.0 with processing cost retained
                    ↓
ordinary inherited policy and unchanged sensors choose movement
                    ↓
post-step observer compares realized destination with no-move position
```

`reverse-spatial-processing-support` changes only the orientation of the analytic support surface. It does not reverse or modify resource geography, renewal targets, residual material, genotype, inheritance, RNG state, policy features, action feasibility or processing-energy rates. The orientation flag is checkpointed and is published in manifests, scientific-validity metadata and metric rows.

The observer reconstructs pre-step store demand for entities present on both sides of a step and samples the next-tick support field at the realized destination and the periodic no-move position. It reports destination-minus-stay support gain, movement/gradient cosine, inventory-weighted exposure and channel store-support correlation. Bilinear sampling is diagnostic only; authoritative metabolism continues to use the existing cell-sampled multiplier.

No response statistic feeds policy, fitness, reproduction, world fields or intervention selection. Original/reversed/neutral contrasts identify registered support interventions only. They cannot by themselves establish migration, specialization, coexistence, ecotypes or ecological roles.

## v0.60 D3-G nested sample-support boundary

D3-G separates source evolution, acute intervention response, and interpretation eligibility:

```text
unintervened source trajectory
        ↓ all predeclared checkpoints retained
seed / checkpoint full-world state
        ├─ original support, fixed acute window
        ├─ reversed support, fixed acute window
        └─ neutral support, fixed acute window
                    ↓
read-only response and sample-support observers
                    ↓
acute eligibility and evolutionary eligibility reported separately
```

The source run disables expensive long-run output diagnostics that have no feedback to world state. World mechanics, policy, RNG, costs, checkpoint contents and branch interventions remain unchanged.

Sample-support accounting uses the seed/checkpoint panel as the nested experimental unit. Movement events, entity-ticks and observation windows are measurement support within that panel, not independent replicates. Every predeclared checkpoint is represented by either a completed panel or an explicit unavailable record. No endpoint-dependent replacement is permitted.

The acute branch ledger starts from checkpoint inventory and cumulative counters, subtracts checkpoint baselines, and closes only the branch interval. This prevents tick-zero history from hiding a branch-window accounting error.

Density-preserving scale configs increase world area, grid cells, initial entities and maximum entities by the same area factor. Cell size and entity density remain fixed. Scale changes no reward, protection, role, genotype, mutation, cost or per-cell environmental parameter.

## v0.61 D3-H matched-control and residue-settlement boundary

D3-H corrects two measurement boundaries without changing policy or ecology.

### Residue numerical provenance

The external residue pool remains float32 world state. Two float64 diagnostic accumulators record finite-precision settlement:

```text
residue field settlement
= residue after diffusion/release + released - residue before update

residue deposit settlement
= residue after sparse writeback - residue before writeback - requested deposit
```

The checkpoint-relative ledger is therefore:

```text
checkpoint residue
+ physical deposits
+ field settlement
+ deposit settlement
= physical release
+ final residue
```

The settlement terms never feed back into state, policy, fitness, reproduction, or environmental dynamics. Older checkpoints are restored with zero historical counters; only post-restore settlement is measured.

### Matched orientation controls

```text
seed/checkpoint state
        ├─ original active
        ├─ original neutral
        ├─ reversed active
        └─ reversed neutral
                    ↓
active-minus-neutral within each observer orientation
```

Applying reversal and neutralization together leaves processing execution neutral while retaining the reversed analytical surface for the read-only observer. This separates support execution from the coordinate system used to measure movement alignment.

The cross-scale audit accepts legacy three-arm and current four-arm results. It can summarize original active-minus-neutral effects from legacy files, but marks their reversed effect unidentified. Seed is the independent unit; checkpoints remain nested observations.

## v0.62 D3-I nested matched-effect inference boundary

D3-I formalizes the experimental hierarchy after the four-arm causal design is complete:

```text
seed
  └─ checkpoint panel
       └─ fixed observation window
            └─ entity movement events
```

Only the seed is an independent replication unit. Checkpoints are equally weighted repeated panels within a seed. Fixed windows are used to audit temporal sign stability, and movement events support measurement precision only; neither increases the independent sample count.

For each support orientation the audit computes:

```text
panel effect = active branch metric - orientation-matched neutral metric
seed effect  = equal mean of eligible checkpoint effects
scale effect = equal mean of seed effects
```

The audit also reports leave-one-checkpoint and leave-one-seed ranges. Exact seed-level sign flips enumerate all sign assignments when there are at most 20 seeds, but the result is descriptive and never the sole gate.

The default replication boundary requires at least eight independent seeds per scale, positive seed means in at least 75% of seeds for each orientation, and both orientations positive in at least 75% of seeds. These thresholds affect interpretation only. They do not alter policy, world state, reproduction, checkpoint selection, reruns, or population survival.

Legacy three-arm results remain readable for original-orientation descriptions, but cannot enter matched reversed inference. Invalid interval ledgers or stored contrast mismatches are excluded from matched inference and retained in the audit record.


## v0.63 GPU-first execution boundary

Production orchestration uses `auto`. Availability selects execution, while parity selects scientific acceptability:

```text
requested auto/gpu
    ├─ usable CUDA/CuPy + hybrid semantics → persistent HybridGpuRuntime
    └─ unavailable device/runtime          → recorded CPU fallback

cross-backend validation
    └─ tests/test_parity.py
       ├─ stage outputs
       ├─ persistent device mirrors
       └─ complete checkpoint-authoritative semantic state
```

The runtime does not silently relabel CPU fallback as GPU execution. The manifest records requested backend, actual execution backend, acceleration state, fallback state and reason. `strict-reference` remains replayable but is not the default route for large runs.

## v0.65 large-population GPU preprocessing boundary

The hybrid runtime keeps regular observation preprocessing on persistent device state:

```text
device genotype + device fields + device entity mirror
    ├─ resource-affinity fixed-budget quantization
    ├─ danger-evidence fixed-budget quantization
    ├─ storage-conditioned policy resource utility
    ├─ oxygen / terrain / wear field update
    ├─ resource, danger and oxygen gradients
    └─ information observation + policy batch
                    ↓
        compact policy/commit payload to CPU
```

Full information observations are downloaded only when parity or evaluation diagnostics require them. Ordinary production ticks download scalar detection summaries instead. Actual H2D/D2H counters remain authoritative; `gpu_device_resident_host_bytes_avoided` is a semantic estimate of host payloads removed by this boundary and is never presented as physical bus measurement.

`Simulation.run()` deliberately defers full device-field synchronization. Any CPU-authoritative phase that needs local physiology obtains only the active-cell oxygen/terrain/wear triplets from `HybridGpuRuntime`; metrics and checkpoints explicitly materialize the current device fields at their low-frequency boundaries. This prevents the deferred host mirror from becoming accidental world state.

The CPU still owns action settlement, births/deaths, relations, subject graphs, knowledge learning and file output. Those are future migration boundaries only after large-population profiling identifies them as dominant. `tests/test_parity.py` covers all registered semantic families and now includes the device preprocessing stage; target-device acceptance still requires `make parity-gpu`.


## v0.66 authoritative reporting boundary

```text
device-authoritative world at tick T
        ↓ report boundary
materialize current environment + information host mirrors
        ↓
metric row / summary tagged reporting_state_tick = T
```

Checkpoint writes and reporting are independent schedules. A checkpoint may
materialize device state for replay, but a report never assumes that the latest
checkpoint is current. This prevents mixed-age rows in which entity counters
are from tick T while residue, roundoff or information fields come from an
earlier checkpoint. Materialization is observational and does not feed values
back into the world.

Before stepping, each run writes `simulation-run-plan-v1` with its fixed target,
backend and output cadences. The plan is provenance, not a scheduler, and
explicitly forbids outcome-conditioned schedule changes.

## v0.67 demographic-selection validity boundary

```text
canonical lifecycle settlement
        ├─ death signature counts (energy / integrity / age overlaps)
        ├─ births and successful-parent cohorts
        └─ living lineage + generation state
                    ↓ fixed evolution window
population fraction + effective lineages + replacement depth
                    ↓ offline audit only
mechanism-valid / demographic-valid / evolutionary-valid classification
```

The validity audit has no world reference and cannot modify a run. A seed is the
independent unit; periodic windows are repeated measurements. Population floors
and generation thresholds govern interpretation only. Runs that collapse before
turnover remain archived as bottleneck/failure-mode evidence and are never
silently replaced.

## v0.69 demographic-regime resolution boundary

```text
fixed initialization
        ↓
early contraction / trough
        ↓ fixed diagnostic windows
population level + low recent slope + low span change
        + founder-lineage concentration
        + current heritable variation
        + descendant replacement
        + unique/effective successful parents
        + parent-contribution concentration
        ↓ offline only
candidate burn-in rule for future independent seeds
```

The runtime tracks successful parent contributions by stable entity ID. Sample count, unique contributor count and inverse-Simpson effective contributor count are separate quantities. The progress tracker checkpoints the in-progress parent contribution map so branch continuation preserves exact window semantics.

`se-multi` writes `multi-seed-run-plan-v3` before starting the first seed and runs `demographic-selection-validity-audit-v3` after all available progress streams complete. Outcome-dependent seed replacement remains forbidden.

An active rebound is not a settled source. A post-bottleneck source rule is design provenance, not retrospective evidence. It can only be applied as a fixed burn-in rule to new independent seeds. Pilot windows used to derive the rule cannot be reused as confirmatory effect samples.


## v0.70 bounded GPU allocator-cache boundary

The hybrid runtime separates live semantic device state from allocator-owned free blocks. `GpuMemoryPoolController` runs only after a completed step, when transient observation and policy arrays have left scope. It may call the backend allocator's free-block operation only when unused cached bytes exceed the configured limit.

Persistent entity mirrors, environment fields, information fields and spatial buffers remain referenced and cannot be released by this operation. The controller therefore changes allocation lifetime, not simulation state. Memory-pressure fallback is deliberately absent: a run either continues on its resolved backend or fails while retaining its latest scheduled checkpoint.

Allocator telemetry belongs to operational provenance. It is not included in checkpoint semantic parity and is not evidence of selection validity.

## v0.71 tiered exploration boundary

```text
existing large-run demographic anchor
        ↓ readiness audit
within-run support ≠ independent confirmation
        ↓
smoke → screen → disjoint replication
        ↓ explicit promotion
large long confirmation on new seeds
```

`exploration-readiness-audit-v1` reads completed selection-validity output and separates population, descendant, reproductive-contributor and current-strategy support from independent-seed count, founder-lineage breadth and stable-source readiness.

`tiered-exploration-plan-v1` fixes the candidate, config hash, seed set, output, backend and horizon before execution. `se-multi` validates the invocation against this plan. Stage promotion cannot reuse seeds, and large long execution requires an explicit confirmation-stage flag.

The protocol is observational and scheduling-only. It does not alter simulation state, thresholds inside the world, survival, reproduction, diversity or selection pressure.
