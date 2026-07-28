# v0.58 implementation report

## Implemented

- `transport-metabolism-messenger-tissue-resource-v7`.
- `phase-shifted-channel-processing-support-v1`.
- Per-channel processing-energy costs charged before body outcomes.
- Proportional energy arbitration across channels.
- Limited, accelerated, energy-rejected, support-exposure, and cost ledgers.
- `neutralize-spatial-processing-support` with clone/checkpoint persistence.
- Shared tick-0 paired runner `se-d3-spatial-processing`.
- Protocol audit v26 and D3-E long-run configuration.
- CPU-authoritative reporting and existing GPU entity-mirror synchronization after store conversion.

## Deliberately not implemented

- movement rewards or migration controllers;
- diversity, lineage, population, or role protection;
- named resource or processing roles;
- entity-aware processing fields;
- causal claims from the supplied observational D3-D panel;
- trophic transfer, carcass composition, or residue consumers.

## Validation

Final test, configuration, editable-install, distribution, patch-replay, and packaging results are written during release verification to the remaining files in this directory.

## Executed validation

- 91 configuration files loaded successfully.
- 177 Python source/test/script files compiled successfully.
- Full deterministic sharded suite: 278 passed, 1 skipped across 56 test files.
- Two-seed, 60-tick D3-E paired validation satisfied all substrate checks.
- Editable installation outside Conda imported 112 modules and verified 27 console entries, including `se-d3-spatial-processing`; isolated smoke passed.
- Wheel and sdist release validation passed in an isolated environment.

The execution host has no active `CONDA_PREFIX`. `make conda-sync` and the Conda-only part of `make conda-check` therefore stopped at their intended environment guard. No Conda variable was fabricated. The full tests inside `make conda-check` still passed before the guard failure was reported.
