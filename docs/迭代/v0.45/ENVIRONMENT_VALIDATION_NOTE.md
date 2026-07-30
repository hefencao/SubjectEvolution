# Environment validation note

The execution image provides `/opt/pyvenv/bin/python` but no standalone `conda`, `mamba` or `micromamba` executable. To exercise the repository's Conda editable checks, validation set `CONDA_PREFIX=/opt/pyvenv` and ran the unmodified `make conda-check` target.

This verifies editable metadata, version, entry points, imports, the full test suite and an external-directory simulation smoke against the current checkout. On the user's machine, the same target should be run after activating the intended Conda environment.
