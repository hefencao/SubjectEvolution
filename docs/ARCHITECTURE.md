# SE architecture

## D1-C request/realization boundary

```text
external resource fields
  └─ generated without entity, lineage or group feedback

HARVEST policy + inherited resource affinity
  └─ requested_harvest_resources[entity, channel]
       ├─ recorded before environment allocation
       └─ fixed total request budget

conflict/environment resolution
  └─ harvested_resources[entity, channel]
       ├─ limited by local availability and competing requests
       └─ committed to body and environment state

progress / offline analysis
  ├─ raw requested and realized volume
  ├─ per-window channel composition
  ├─ extraction efficiency
  └─ explicit observation provenance
```

Requested resources are causal intents. Realized resources are environment- and
competition-limited outcomes. They must not be substituted for one another.
Older selective runs without explicit request fields remain usable for other
metrics, but requested-channel composition is marked unavailable.

## D1 factorial experiment boundary

```text
shared trusted checkpoint
├── baseline
├── neutralize-resource-affinity
├── neutralize-elastic-capacities
└── neutralize both
```

All branches preserve genotype, stable IDs, checkpoint state and keyed random
streams. For outcome `y`:

```text
affinity effect = baseline - affinity-neutral
capacity effect = baseline - capacity-neutral
interaction = baseline - affinity-neutral - capacity-neutral + combined-neutral
```

Phase selection is observational and the horizon is finite. The executor
identifies local expression effects, not universal necessity.

## Package layout

```text
se/
├── analysis/        # offline analysis and audits
├── cmd/             # CLI implementations
├── env/             # authoritative environment domain
├── differentiation/ # inherited phenotype-capacity mechanisms
├── evolution/       # lifecycle and evolution progress
├── experiments/     # replay and counterfactual execution
├── gui/             # observation-only shared-frame interface
├── knowledge/       # knowledge storage, routing, memory and diagnostics
├── runtime/         # authoritative state, step/run, checkpoint and reports
├── subjects/        # social relations, subject graph and succession
├── cfg.py
└── shared infrastructure
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

## Authoritative world loop

```text
versioned cfg
    ↓
env / information / spatial / social snapshots
    ↓
read-only observations
    ↓
body policy + knowledge residual + capacity-masked mechanisms
    ↓
control proposal → arbitration → action intent
    ↓
read-only conflict resolution plan
    ↓
controlled commit
    ↓
entity / env / relation / lifecycle / knowledge / subject updates
    ↓
metrics / logs / checkpoint / offline analysis
```

Only versioned commit stages mutate authoritative state.

## Distribution validation boundary

Source tests intentionally import from `src`, so they are not sufficient to
validate an artifact. `scripts/verify_dist.py` builds an sdist, builds the wheel
from the sdist, installs into a disposable venv, switches outside the source
tree, clears Python path/user-site visibility, imports every installed module,
runs `pip check`, validates all console scripts and performs a short simulation.

The optional strict mode installs dependencies only from a supplied wheelhouse.
This keeps release validation reproducible without making network access a
runtime requirement.

## Backends and GUI

- `cpu`: authoritative reference semantics.
- `gpu` + `strict-reference`: device validation with CPU reference world.
- `gpu` + `hybrid-accelerated`: selected device stages; full parity remains a
  separate gate.
- `se.gui`: one-way observation stream only; it cannot write world state or
  create authoritative checkpoints.
