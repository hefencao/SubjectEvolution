# v0.35 implementation report

## Scope

This release changes package and file paths only. World equations, config fields, schemas, keyed randomness and commit order are unchanged.

## Naming policy

Adopted abbreviations:

- `se`: project/package identity;
- `env`: environment domain;
- `cmd`: command implementations;
- `cfg`: configuration module;
- `sim`: runtime simulation engine;
- `gui`: existing standard acronym.

Retained full names:

- `analysis`, `experiments`, `evolution`, `knowledge`, `subjects`, `runtime`;
- scientific JSON fields and schemas.

This avoids short but ambiguous paths such as `ana`, `exp`, `evo`, `know` and `subj`.

## Structural changes

- `src/subject_evolution` → `src/se`;
- removed generic `domains/` and `interfaces/` levels;
- `domains/environment` → `env`;
- `domains/evolution` → `evolution`;
- `domains/knowledge` → `knowledge`;
- `domains/subjects` → `subjects`;
- `interfaces/gui` → `gui`;
- `commands` → `cmd`;
- `config.py` → `cfg.py`;
- `runtime/simulation.py` → `runtime/sim.py`;
- `analysis/structure_environment.py` → `analysis/structure_env.py`;
- removed the final historical checkpoint bridge.

## Token/readability effect

Across 265 current source/test import lines that reference the project package, canonical path characters are reduced from a mapped 19,106 to 12,953: **32.2%**. Average line length falls from 72.1 to 48.9 characters.

The most frequent environment path changes from 37 characters (`subject_evolution.domains.environment`) to 6 (`se.env`).

## Config and script migration

- all 69 JSON configs load and validate;
- scientific JSON keys remain unchanged;
- three filenames use `env` instead of `environment`/`multienvironment`;
- five shell scripts plus `run_gpu.sh` and `run_gpu.ps1` use `se` paths;
- console scripts are `se`, `se-multi` and `se-gui`;
- no compatibility aliases are installed.

## Documentation policy

Current source distributions include canonical docs and the current `docs/v0.35` release report only. Detailed historical release reports remain available in their corresponding previous release bundles instead of being duplicated into every new source package.
