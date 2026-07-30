# D3-G preregistered sample-support and acute-response protocol

## Problem identified in the supplied D3-F panel

The supplied three-seed, 1500-tick triplets are complete mechanism audits, but the cumulative response statistics are not population-balanced long-run samples.

A fixed 300-tick reanalysis shows:

- the first 300 ticks contribute 43.7%–53.7% of inventory-eligible entity-ticks;
- the first 300 ticks contribute 52.8%–61.3% of resource movements;
- every branch first falls below 100 alive at an observed tick between 330 and 420;
- no post-burn-in branch keeps at least 100 alive across all observation snapshots;
- there are only three independent seed triplets, regardless of the number of movement events;
- the supplied result schema does not contain enough generation history to authorize evolutionary inference.

The D3-F mechanism and ledger findings remain valid. The single cumulative mean is no longer treated as adequate evidence for a long-run response effect.

## Separate acute response from evolutionary evidence

D3-G runs an unintervened source trajectory to every predeclared checkpoint. Each available checkpoint is restored into:

1. `original-support`;
2. `reversed-support`;
3. `neutral-support`.

The default branch window is 120 ticks. Checkpoints within a seed are nested repeated panels, not independent seeds. Every requested checkpoint remains in the result, including checkpoints that are unavailable after source extinction or fail sample-support requirements. No replacement seed or checkpoint is selected from outcomes.

## Default acute sample-support requirements

The defaults are interpretation guards, not world rules:

- minimum alive throughout the branch window: 100;
- minimum alive entity-ticks: 12,000;
- minimum inventory-eligible entity-ticks: 6,000;
- minimum resource movements: 1,000;
- minimum unique observed entities: 100;
- minimum effective lineage entity-ticks: 20;
- maximum largest-lineage entity-tick fraction: 0.25.

Failing a requirement does not stop, retry, rescue, protect, or remove a run. It marks the panel as insufficient for the registered acute response analysis.

## Evolutionary support is separate

A checkpoint is not evolution-qualified merely because its acute panel has many movements. The default descriptive gate additionally requires:

- cumulative births at least equal to the initial entity count;
- mean living generation at least 1;
- maximum living generation at least 3.

These thresholds do not establish adaptation. They only prevent a largely founder-generation population from being described as a long-run evolutionary result.

## Exact interval accounting

Every acute branch reports checkpoint-relative ledgers rather than relying only on counters accumulated since tick zero:

```text
checkpoint external inventory
+ interval source
+ interval residue release
+ interval field settlement
= interval harvest
+ interval sink
+ branch-end external inventory
+ interval harvest settlement
```

The residue ledger similarly includes checkpoint-start residue. This prevents the long source history from masking an acute-window accounting error.

## Scale controls

The base, 1.5× linear, and 2× linear configurations preserve:

- entity density;
- maximum-entity density;
- grid-cell physical size;
- per-cell resource capacity and renewal parameters;
- all entity costs, genes, mutation, policy and intervention semantics.

Scaling does not protect any entity or lineage. It raises the number of simultaneously observed entities and lineages while retaining the same local rules. The unchanged normalized wave vectors make larger maps a map-scale test with proportionally broader physical opportunity waves.

## Interpretation boundary

D3-G can establish whether an acute orientation response is repeatedly observable in preregistered, sample-supported checkpoint panels. It cannot by itself establish adaptive evolution, migration cycles, specialization, coexistence, ecotypes, trophic transfer, or named roles.
