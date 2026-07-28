# SE project status

Version: **0.53.0**

## Current causal chain

```text
orthogonal resource and abiotic fields
→ inherited resource affinity and elastic capacities
→ fixed four-slot inherited functional operators
→ inherited feed-forward composition
→ regulatory requests separated from physiological execution
→ inherited transport / reserve / conversion / fatigue / repair / messenger parameters
→ conservative non-negative flow ledger and starvation debt settlement
→ inherited bounded raw-resource stores
→ delayed per-channel conversion through the existing resource-effect matrix
→ future spatial resource processing, detritus, consumption, defense and trophic transfer
→ ecological differentiation tests only after those processes create distinct demands
```

## D2-L v3 evidence

The supplied three-seed, 1500-tick rerun uses `transport-metabolism-messenger-tissue-v3`. Every seed has finite non-negative physiology flows, messenger turnover, finite precursor turnover, computation cost, fatigue turnover, and damage/repair. The result supports retaining the conservative physiology substrate. It does not establish a named organ, stable niche, food chain, or module-copy rationale.

## D3-A resource metabolism

The opt-in pair is:

- functional schema `expression-gated-regulatory-resource-metabolism-v6`;
- input schema `internal-homeostasis-local-resources-abiotic-stores-feedforward-v5`;
- physiology schema `transport-metabolism-messenger-tissue-resource-v4`.

D3-A adds eight inherited parameters: four store capacities and four conversion capacities. All channels share equal base values. Harvested raw resources enter bounded stores and can affect body state only on later ticks. Store occupancy is visible to the same fixed operators, allowing behavior to respond to internal inventory without assigning resource roles.

The ledger is:

```text
cumulative stored
= cumulative converted
+ cumulative decay
+ cumulative death loss
+ final stores carried by living entities
```

Death loss is currently explicit dissipation. Detritus recycling is intentionally deferred until a conserved external matter-transfer process is designed.

## Still incomplete

- spatially distinct processing opportunities and migration cycles;
- excretion, detritus, scavenging, and external matter recycling;
- consumption of other entities and corresponding defense;
- reproduction investment supplied through delayed stores rather than the current body outcome alone;
- stable coexistence, ecotypes, and trophic-chain evidence;
- dynamic module topology or copy-number evolution;
- deterministic inherited sparse routing beyond continuous costed routes.
