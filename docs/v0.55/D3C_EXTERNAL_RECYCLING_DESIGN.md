# D3-C identity-preserving external recycling

## Motivation

D3-B closes the intake boundary: raw resource that cannot fit inherited internal storage remains in the environment. Its supplied three-seed result also closes both intake and internal-store ledgers once floating-point residuals are judged relative to harvested mass.

The next missing transfer is material already inside entities:

- raw material lost through internal-store decay;
- unconverted raw material carried when an entity dies.

In resource-v5 these flows are explicit but dissipative. D3-C adds a minimal external transfer substrate without introducing a biological decomposer or a resource role.

## Versioned boundary

D3-C is enabled only by:

```text
transport-metabolism-messenger-tissue-resource-v6
```

All earlier physiology schemas retain their archived behavior. Resource-v5 remains the conservative-intake schema with dissipative store decay and death loss.

## External state

The environment conditionally owns:

```text
resource_residue[4, grid_y, grid_x]
```

The four channels retain exactly the same identity as the four raw external resource channels. There is no fifth “detritus resource”, no conversion matrix and no named waste type.

## Sources

### Internal-store decay

For each living entity and channel, the amount already recorded by `resource_store_decay` is deposited at the entity's current cell.

### Death-carried raw stores

Before death state is committed, the entity's remaining four-channel `resource_store` is deposited at its death cell. The existing `resource_store_death_loss` term remains in the internal-store ledger; under v6 it denotes transfer out of the carrier rather than destruction from the world.

No energy, tissue, structure, integrity, messenger precursor or other body state is converted into residue in D3-C.

## Tick ordering

The authoritative sequence is:

1. diffuse and release residue present at tick start;
2. apply ordinary external resource regeneration;
3. convert and decay current internal stores;
4. after the environment update, deposit that tick's store decay;
5. after death resolution, deposit death-carried raw stores.

Therefore new residue remains external for at least one full tick before release.

## Diffusion and release

To avoid adding channel-specific hand-authored parameters:

- residue diffusion reuses each channel's existing resource diffusion rate;
- residue release reuses each channel's existing internal-store decay rate;
- release returns only to the same resource channel;
- release is limited by current free capacity of the external resource field;
- unreleased material remains in the residue field.

The reuse is explicit in the protocol audit and can be replaced by a future versioned transport schema if long-run evidence shows that external residence needs an independent axis.

## Ledgers

The existing internal ledger remains:

```text
stored = converted + store decay + death-carried transfer + final living store
```

D3-C adds:

```text
store decay + death-carried transfer = external residue deposited
external residue deposited = residue released + final external residue
```

Diffusion is internal redistribution and does not enter the scalar ledger.

## Interpretation boundary

D3-C establishes only a conservative external material-return path. It does not establish:

- decomposers or scavengers;
- carcass consumption;
- trophic transfer;
- ecological coexistence;
- migration;
- a named metabolism;
- module-copy benefit.
