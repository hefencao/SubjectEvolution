# SE architecture

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

Per-module diagnostic rounding never feeds the authoritative preference. Partial
neutralization preserves genotype and removes only the selected module
expression and its proportional maintenance/development cost. Analysis and
experiments depend on runtime; runtime does not depend on the D2 audit.

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

The module layer cannot choose an action, alter resource assimilation, modify
resource-gradient utility, create a world field, or publish to movement,
signalling, sharing, memory or social control. This narrow boundary prevents a
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
metadata and console scripts all refer to the exact checkout. Ordinary source
edits require no reinstall. `make conda-check` adds tests and an external smoke
with an empty `PYTHONPATH`.

Wheel/sdist validation remains a release-transfer audit and is not the local
runtime environment.

## Backends and GUI

- `cpu`: authoritative reference semantics.
- `gpu` + `strict-reference`: GPU availability validation with CPU-authoritative world.
- `gpu` + `hybrid-accelerated`: experimental accelerated stages; parity remains separate.
- `se.gui`: observation-only shared-frame publication.
