# D3-B conservative storage-constrained intake

## Purpose

D3-B fixes the environmental boundary of D3-A without assigning resource roles or introducing new ecological actors.

## Versioned semantics

- legacy replay: `transport-metabolism-messenger-tissue-resource-v4`;
- conservative intake: `transport-metabolism-messenger-tissue-resource-v5`;
- intake contract: `storage-room-constrained-preharvest-v2`.

The intake contract is derived from the physiology schema rather than stored as an additional configuration field. This preserves the serialized shape and exact checkpoint payload of legacy v4 configurations.

## Raw-unit capacity calculation

For each entity and channel:

```text
assimilated room = inherited capacity - current store
raw environmental room = assimilated room × affinity scale / affinity multiplier
admitted raw request = min(unconstrained raw request, raw environmental room)
capacity rejected = unconstrained raw request - admitted raw request
```

Only admitted raw requests enter environmental conflict resolution. Capacity-rejected material remains in the external resource field.

## Policy observation

The normalized local resource utility is multiplied by current free-store fraction for that channel. This is a physical opportunity constraint, not a reward: an entity with no room cannot treat the channel as immediately usable, while partially free stores preserve proportional opportunity.

## Ledger boundaries

D3-B records:

- unconstrained request;
- admitted request;
- capacity rejection before environment commit;
- environmental shortfall after competition;
- actual harvested resource;
- assimilated storage;
- post-assimilation overflow;
- conversion, decay, death loss and final living store.

Post-assimilation overflow must be zero within floating-point tolerance. The existing internal store ledger remains unchanged.

## Explicit exclusions

D3-B adds no:

- detritus or carcass pool;
- named food or nutrient channel;
- metabolic role label;
- ecological role;
- diversity reward or protection;
- module copy-number or topology change;
- stable-niche claim.

External recycling is the next candidate only after this corrected intake boundary remains stable in a long run.
