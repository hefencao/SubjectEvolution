# Environment validation note

The execution host exposes `/opt/pyvenv` but no standalone `conda`, `mamba`, or `micromamba` executable. Validation set `CONDA_PREFIX=/opt/pyvenv` and ran the project's unchanged editable-install verification.

`make conda-sync` completed successfully. `scripts/verify_conda_editable.py --require-conda --smoke` confirmed version `0.49.0`, the current source root, 96 importable modules, 18 console entries, and an external-directory CPU smoke.

The user should activate the intended local Conda environment and run `make conda-sync` once because v0.49 changes version metadata and console entries.
