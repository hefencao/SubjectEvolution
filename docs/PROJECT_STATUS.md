# SE project status

Version: **0.54.0**

## Current causal chain

```text
orthogonal resource and abiotic fields
→ inherited affinity and elastic capacities
→ fixed inherited functional operators and feed-forward composition
→ regulatory requests separated from physiological execution
→ inherited transport / reserve / conversion / fatigue / repair / messenger parameters
→ conservative non-negative physiological flow ledger
→ inherited bounded raw-resource stores
→ at least one-tick delayed conversion through the existing resource-effect matrix
→ storage-constrained environmental intake before resource commit
→ future conserved excretion / detritus / carcass recycling
→ spatial separation of collection and processing opportunities
→ entity consumption, defense and trophic transfer
→ ecological differentiation tests only after these processes create distinct demands
```

## D3-A evidence and correction

The supplied D3-A run completed three 1500-tick seeds. Storage, conversion, all four channels, genetic variation, and the internal store ledger remained active in every seed. Conversion consumed about 93% of cumulatively stored material.

The run also exposed a semantic defect: post-harvest overflow was about 59%–62% of successful stored material. Because the environment was debited before capacity was checked, this overflow vanished instead of remaining external or entering a conserved detritus pool. Population endpoints from this run must not be interpreted before correcting that loss.

## D3-B conservative intake

The opt-in pair is:

- functional schema `expression-gated-regulatory-resource-metabolism-v6`;
- input schema `internal-homeostasis-local-resources-abiotic-stores-feedforward-v5`;
- physiology schema `transport-metabolism-messenger-tissue-resource-v5`;
- derived intake contract `storage-room-constrained-preharvest-v2`.

The inherited store room is converted into maximum raw request units using the entity's resource affinity. Only that admitted request enters environmental conflict resolution. Capacity-rejected raw resource remains in the cell. The policy's resource utility is multiplied by channel-specific free-room fraction, so a full store does not advertise an unusable opportunity.

The historical resource-v4 schema preserves v0.53 post-harvest overflow behavior for exact checkpoint and result replay.

## Still incomplete

- external excretion, detritus, carcass and scavenging matter pools;
- spatially distinct collection and processing opportunities;
- migration cycles driven by stored inventory and environmental seasonality;
- consumption of other entities and corresponding defense;
- reproduction investment supplied through delayed stores;
- stable coexistence, ecotypes and trophic-chain evidence;
- dynamic module topology or copy-number evolution;
- deterministic inherited sparse routing beyond continuous costed routes.
