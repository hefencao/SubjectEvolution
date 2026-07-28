# Environment validation note

The execution host provides the active Python prefix at `/opt/pyvenv` but no standalone `conda`, `mamba`, or `micromamba` executable. Validation therefore set `CONDA_PREFIX=/opt/pyvenv` and ran the repository's unmodified editable-prefix checks.

Completed in the final source tree:

- `make conda-sync` after the v0.51 version and console-entry changes;
- `make conda-check` without reinstalling, including all test shards, exact editable-root verification, 102 importable modules, 20 console entries, and an external-directory CPU smoke;
- `make release-check`, including fresh source tests and isolated sdist → wheel → disposable-environment validation.

This proves the repository's prefix and editable-install invariants in the available environment. The user's normal workflow remains to activate the intended Conda environment locally before running these targets.
