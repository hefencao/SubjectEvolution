# SE project status

Version: **0.57.0**

## Current causal chain

```text
role-free four-channel external resource and abiotic fields
→ persistent moving channel-specific abiotic renewal targets
→ explicit physical source / sink / release / harvest fluxes
→ separately recorded float32 inventory settlement
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

## Supplied D3-D result

The supplied three-seed, 1500-tick panel supports only the D3-D substrate claim:

- renewal source is observed in every seed;
- renewal sink is observed in every seed;
- identity-preserving external recycling closes in every seed;
- final resource effective dimensions are about `2.86`–`2.98`;
- the v1 open external-resource ledger is marked invalid in every seed.

The final multidimensional fields are observational evidence that the moving role-free target continues to supply distinct opportunities. They do not establish migration, collection-processing specialization, coexistence, trophic transfer or an ecological role.

## v0.57 ledger correction

The v0.56 ledger accumulated source, sink, release and admitted harvest in `float64`, but the authoritative environment fields and segmented harvest commits settle in `float32`. The difference is small, signed and cumulative. It must not be relabeled as a physical source or sink.

v0.57 records:

- `resource_field_roundoff_total`;
- `resource_harvest_roundoff_total`;
- their signed net numerical adjustment.

The authoritative open-system identity is:

```text
initial + source + release + field settlement
= harvest + sink + final + harvest settlement
```

A same-seed 300-tick validation closes the corrected identity at near machine precision while retaining an explicit unadjusted residual. No state transition or ecological mechanism was altered.

## Decision

Retain D3-D and the D3-C recycling substrate. Do not advance the scientific chain solely from the old v1 result. Rerun the three 1500-tick seeds with D3-D results v2; reconsider collection-processing coupling only after corrected ledgers close and opportunity dimensions remain persistent.

## Development workflow

`make conda-sync` clears project bytecode, installs the exact checkout editable, and verifies static source, imported package, installed metadata, direct URL and editable root. `make test` runs the full sharded suite. `make conda-check` repeats tests plus installed console smoke. `make release-check` audits wheel and sdist transfer separately.

## Still incomplete

- a v2-schema rerun of the supplied three-seed D3-D long horizon;
- evolved coupling between collection location, internal inventory and processing throughput;
- migration cycles driven by moving resource opportunities and stored inventory;
- externalization of metabolic byproducts and non-store body material;
- evolved uptake or processing of residue as a distinct opportunity;
- consumption of other entities and corresponding defense;
- reproduction investment supplied through delayed stores;
- stable coexistence, ecotypes and trophic-chain evidence;
- dynamic module topology or copy-number evolution;
- deterministic inherited sparse routing beyond continuous costed routes.
