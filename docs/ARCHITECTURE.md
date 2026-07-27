# SE architecture

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
the v0.41 authoritative module path.

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
