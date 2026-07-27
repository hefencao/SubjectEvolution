# Validation environment note

The delivery container provides Python at `/opt/pyvenv/bin/python` but does not
provide a `conda`, `mamba` or `micromamba` executable. To exercise the project's
required editable workflow, validation used:

```bash
CONDA_PREFIX=/opt/pyvenv make conda-sync
CONDA_PREFIX=/opt/pyvenv make conda-check
```

The verifier confirmed that the active Python is inside the declared prefix,
the distribution is editable and points to this exact checkout, version metadata
is `0.42.0`, all 84 package modules import, all seven console entries are current,
and a source-tree-external two-tick smoke run succeeds. The full test suite also
passed inside `make conda-check`.

This is a faithful execution of the repository's prefix/editable validation, but
it is not a claim that a real Conda executable was available in this container.
The same commands should be rerun in the user's activated Conda environment after
applying the patch or extracting the project package.
