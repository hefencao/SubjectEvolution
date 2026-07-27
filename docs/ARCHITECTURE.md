# SE architecture

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

## Release boundary

`release-check` validates a disposable venv and intentionally leaves the caller
unchanged. `release-env` validates the same sdist-derived wheel in a persistent
`.release-env/venv`. Neither Make nor a child process can activate a venv in the
parent zsh; the user must `source .release-env/venv/bin/activate` or invoke the
script by its explicit path.

The artifact verifier:

1. builds an sdist;
2. builds the wheel from that sdist;
3. installs an optional prior wheel;
4. force-reinstalls the candidate;
5. clears source/user paths and runs outside the checkout;
6. imports every installed module;
7. validates all console scripts;
8. executes single- and multi-seed exact-checkpoint smoke runs.

## Backends and GUI

- `cpu`: authoritative reference semantics.
- `gpu` + `strict-reference`: GPU availability validation with CPU-authoritative world.
- `gpu` + `hybrid-accelerated`: experimental accelerated stages; parity remains separate.
- `se.gui`: observation-only shared-frame publication.
