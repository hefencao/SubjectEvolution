# v0.60 implementation report

## Scope

v0.60 treats the low-population D3-F result as an experimental-design problem rather than evidence for another ecological mechanism. It adds no reward, rescue, diversity protection, role label, processing-support sensor, or migration controller.

The supplied D3-F result remains a valid mechanism and ledger audit. Its long-horizon cumulative response means are not treated as population-balanced or evolutionary evidence.

## Supplied-result sampling audit

`se-d3-response-adequacy` partitions the supplied trajectories into fixed, non-overlapping time blocks and treats the seed/checkpoint panel as the independent experimental unit. Movement events remain temporally and genealogically clustered observations.

For the supplied three-seed triplets:

- the first 300 ticks contribute 43.7%–53.7% of inventory-eligible entity-ticks;
- the first 300 ticks contribute 52.8%–61.3% of resource movements;
- every branch first falls below 100 alive at an observed tick between 330 and 420;
- no post-burn-in branch maintains the registered population floor;
- the source schema lacks sufficient generation history for evolutionary inference.

These findings retain the negative response observation while narrowing its scope: the current system does not show a strong repeated positive alignment with processing support, but the run cannot estimate a population-balanced long-run or evolutionary effect.

## D3-G preregistered acute checkpoint panels

`se-d3-processing-response-panel` runs one unintervened source trajectory per independent seed and saves every predeclared checkpoint that exists. Every checkpoint is restored into:

1. `original-support`;
2. `reversed-support`;
3. `neutral-support`.

The default response window is 120 ticks. Checkpoints within one seed are nested repeated panels, not independent seeds. Missing or sample-insufficient checkpoints remain in the output and are never replaced using outcomes.

Each branch records:

- minimum alive and exact alive entity-ticks;
- inventory-eligible entity-ticks;
- resource movements and unique observed entities;
- effective lineage entity-ticks and largest-lineage contribution;
- births, deaths, age, mean generation and maximum generation;
- windowed response trajectories;
- checkpoint-relative external-resource and recycling ledgers.

Sample-support labels are interpretation metadata only. They do not affect survival, reproduction, movement, resources, lineage persistence, or branch execution.

## Separate eligibility boundaries

The default acute-response support gate requires:

- minimum alive: 100;
- alive entity-ticks: 12,000;
- inventory-eligible entity-ticks: 6,000;
- resource movements: 1,000;
- unique observed entities: 100;
- effective lineage entity-ticks: 20;
- largest-lineage entity-tick fraction no greater than 0.25.

The separate descriptive evolutionary gate requires cumulative births at least equal to the initial population, mean living generation at least 1, and maximum living generation at least 3. Passing these conditions would not establish adaptation; failing them prevents a founder-dominated trajectory from being described as evolutionary evidence.

## Base checkpoint pilot

A seed-60001 base-scale source reached checkpoint 300 with:

- 119 alive;
- about 108.10 effective living lineages;
- mean living generation about 0.0504;
- maximum living generation 1.

All three 300→420 branches completed with valid checkpoint-relative ledgers and more than 1,500 resource movements, but minimum alive fell to 81–87. The panel is therefore retained as mechanism-complete and acute-insufficient. Its generation depth is also insufficient for evolutionary interpretation.

## Density-preserving scale pilot

The 1.5× linear-scale source uses 1,125 initial entities on a 192×192 world with a 48×48 grid, preserving entity density, maximum-entity density and grid-cell physical size. At tick 300 it had:

- 274 alive;
- about 246.96 effective living lineages;
- mean living generation about 0.0547;
- maximum living generation 1.

This shows that unprotected geometric scaling can improve acute population support, but cannot create generation turnover. The full 1.5× acute triplet was not completed on the delivery host and is not reported as response evidence. The 2× configuration is included but was not completed on the delivery host.

## Protocol and compatibility

- Project version: `0.60.0`.
- Protocol audit schema: `se-protocol-audit-v28`.
- Historical D3-F result and checkpoint formats remain readable.
- Two console entries were added:
  - `se-d3-processing-response-panel`;
  - `se-d3-response-adequacy`.
- Two density-preserving scale configurations were added.
- Exact checkpoint-relative material ledgers are tested independently of counters accumulated before the checkpoint.

## Validation

- 93 JSON configurations loaded successfully.
- 183 Python files under source, scripts and tests compiled successfully.
- `make test`: 283 passed, 1 skipped across 59 test files.
- Editable verification: 115 importable modules and 30 registered SE console entries; external empty-`PYTHONPATH` smoke passed.
- `make release-check`: isolated wheel and sdist validation passed.

The delivery host did not have an active Conda environment. `make conda-sync` and the Conda-specific phase of `make conda-check` therefore stopped at the explicit `CONDA_PREFIX` guard. The full test phase of `make conda-check` passed, and non-Conda editable verification was completed without pretending that Conda was active.

## Scientific boundary

v0.60 establishes a measurement and sampling protocol. It does not establish migration, adaptation, specialization, coexistence, ecotypes, trophic transfer, or named ecological roles. A later mechanism change remains gated on repeated orientation-aligned response across independent seeds and sample-supported panels, while evolutionary interpretation additionally requires actual generation turnover.
