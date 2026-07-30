# v0.51 implementation report

## Main correction

v0.50 is retained as an archived replay ABI but is no longer the recommended long-run substrate. v0.51 replaces its four direct body drives with a two-layer regulatory system:

- functional modules publish bounded regulatory requests;
- inherited physiological parameters and conserved dynamic states determine execution.

## Added

- v5 functional, input and output schemas;
- fifteen inherited physiology genes;
- independent mobilization and maintenance messenger pathways;
- shared finite messenger precursor;
- metabolic fatigue and explicit computation cost;
- basal-zero regulatory semantics;
- receptor blockade and bounded state-clamp interventions;
- checkpoint/clone persistence for states, interventions and cumulative flows;
- D2-L configs, CLI and descriptive report;
- v5 diagnostics and protocol audit v19.

## Preserved

- v1-v4 schemas and checkpoint defaults;
- fixed four-slot feed-forward operator topology;
- expression gates and their structural/use costs;
- four-resource harvest interface;
- deterministic keyed randomness;
- ordinary simulation path when v5 is disabled.

## Deliberately absent

- online weight learning;
- arbitrary recurrent topology;
- named hormones or organs;
- multicellular development;
- diversity rewards or lineage protection;
- module copy-number changes.

## Final validation

- 240 tests passed and one expected test was skipped across all 48 test files.
- 83 JSON configurations loaded successfully.
- 157 Python files under `src`, `scripts`, and `tests` compiled successfully.
- The editable installation resolved version `0.51.0`, 102 importable modules, and 20 console entries to this checkout.
- The installed D2-L entry executed a 10-tick CPU smoke with all eight output coordinates active.
- A shared v3 20-tick compatibility run matched v0.50 across 682,409 common checkpoint semantic leaves, 410 common non-timing summary leaves, and 3 × 395 common non-timing metric cells.
- Isolated sdist and wheel installation validation passed.
