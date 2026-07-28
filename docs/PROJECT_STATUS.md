# SE project status

Version: **0.55.0**

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
→ identity-preserving external residual-material deposition, diffusion and release
→ spatial separation of collection and processing opportunities
→ broader body decomposition / excretion and entity-to-entity material transfer
→ ecological differentiation tests only after these processes create distinct demands
```

## D3-B result

The supplied D3-B run completed three 1500-tick seeds. Capacity rejection, storage, delayed conversion, intake-ledger closure and internal-store-ledger closure were present in every seed.

The accumulated post-assimilation residual was about `1.6e-4`–`1.8e-4` per run, but only `6e-9`–`9e-9` relative to per-channel harvested mass. The old summary used a fixed absolute `1e-4` run-level threshold and incorrectly reported failure. The scale-aware reassessment passes all three seeds.

## D3-C external recycling

The opt-in physiology schema is:

- `transport-metabolism-messenger-tissue-resource-v6`.

It retains the D3-B pre-harvest capacity contract and adds one external field:

- four-channel `identity-preserving-spatial-residue-v1`.

Sources are restricted to material already accounted by the internal raw-store ledger:

- internal store decay;
- raw stores carried by entities at death.

Each source deposits at the entity's current cell and preserves its resource channel. The residual field:

- remains external for at least one tick;
- diffuses with the existing same-channel resource diffusion rate;
- releases with the existing same-channel store-decay rate;
- releases only into free capacity in the same external resource field;
- remains in the residual field when external capacity is full.

This is a matter-transfer substrate, not a biological decomposer or scavenger population. Body energy, tissue and structure are not yet converted into external material.

## Still incomplete

- externalization of metabolic byproducts and non-store body material;
- evolved uptake or processing of residual material as a distinct opportunity;
- spatially distinct collection and processing opportunities;
- migration cycles driven by inventory and seasonality;
- consumption of other entities and corresponding defense;
- reproduction investment supplied through delayed stores;
- stable coexistence, ecotypes and trophic-chain evidence;
- dynamic module topology or copy-number evolution;
- deterministic inherited sparse routing beyond continuous costed routes.
