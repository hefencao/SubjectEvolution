# D2-F temporal mediation audit

## Input decision

The paired 300-tick assessment confirms only module 3 across the original 120/300 horizons, through a positive routed-output effect on `target_lineage.mean_energy`. Module 2 fails the cross-horizon confirmation. No positive ecological routed-output outcome is confirmed, and the source-lineage guard remains failed.

The target-lineage alive effect changes from negative in the 120-tick screen to positive in the 300-tick current-horizon summary, but it does not persist in the same paired units with the same material direction. Mean energy therefore cannot be interpreted as fitness or ecological benefit by itself.

## Question

Does module 3 alter a measurable input flow that first changes target-lineage energy stock and later changes reproduction or survival, or is the higher mean energy mainly a survivor-conditioned composition effect?

## Design

D2-F selects module 3 at module level and preserves every lineage already selected before the D2-D intervention. It does not select only responsive lineages.

Each checkpoint-lineage pair retains the existing three branches:

1. `baseline`: routed output and expression cost retained;
2. `output-neutral`: routed output removed, expression cost retained;
3. `expression-neutral`: routed output and expression cost removed.

One execution is observed at offsets 30, 60, 120, 180, 240 and 300 ticks. These offsets are repeated measurements of one causal pair and do not increase the seed or lineage replicate count.

## Read-only measurements

For each target lineage and offset, the experiment records:

- mean, total, quartile and median energy;
- source-lineage survivors and living descendants;
- cumulative births and deaths, including energy, integrity and maximum-age death causes;
- total/mean fertility and reproduction-ready count/fraction;
- cumulative harvested energy after intervention;
- cumulative shared energy received after intervention;
- world alive, mean energy and total energy.

Birth and death counts use stable entity IDs. Harvest/share flows use per-entity cumulative counters differenced across each authoritative step, including the final step of entities that die. No measurement feeds back into policy, world commits or random streams.

## Interpretation gates

A flow-to-energy chain requires a repeated positive harvest or shared-energy effect at or before the first repeated positive mean-energy offset. Mean energy is checked against total energy so a change among fewer survivors is not mislabeled as increased lineage energy stock.

Demographic conversion requires a later repeated favorable change in alive count, source survival, living descendants, births, net population change, reproduction-ready count, or fewer deaths. A simultaneous adverse demographic effect is classified as an energy-demography tradeoff.

Replication is counted independently within each offset and requires at least two seeds and two non-dominant lineage identities in the same material direction. Offsets are never pooled as independent replicates.

## Structural boundary

D2-F adds no module copies, deletion, arbitrary output routing, new physical ports, diversity protection or ecological role labels. Even a completed flow-energy-demography chain cannot bypass the source-lineage guard.
