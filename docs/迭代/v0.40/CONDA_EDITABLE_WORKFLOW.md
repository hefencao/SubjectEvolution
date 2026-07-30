# Conda editable development workflow

## Decision

The normal local runtime is an activated conda environment with one editable
installation of the current checkout. A new wheel does not need to be installed
after every source edit.

```bash
conda activate <your-env>
make conda-sync
```

`conda-sync` executes:

```bash
python -m pip install --no-deps --no-build-isolation -e .
python scripts/verify_conda_editable.py --project . --require-conda
```

`--no-build-isolation` is intentional for offline or restricted conda
environments: the active environment's setuptools/wheel are used instead of
creating a temporary build environment that may try to download build tools.
The conda environment must already contain the project runtime and build
requirements.

## When reinstall is required

An editable reinstall is required after changing:

- `pyproject.toml` version or entry points;
- dependencies or optional dependency groups;
- package discovery/layout metadata;
- the checkout path;
- the active conda environment.

A reinstall is not required for ordinary edits under `src/`, `configs/`,
`tests/`, or analysis code. Those files are read directly from the checkout.

## Daily verification

```bash
make test
```

Before a long run or handoff:

```bash
make conda-check
```

`conda-check` verifies that:

- `CONDA_PREFIX` is active and owns the current Python;
- `se` imports from this exact checkout's `src/se`;
- package, metadata and `pyproject.toml` versions agree;
- `direct_url.json` proves an editable install of this checkout;
- all installed SE modules import;
- all console entry points match `pyproject.toml`;
- a source-tree-external two-tick smoke run succeeds with an empty
  `PYTHONPATH`.

## Artifact builds

Wheel/sdist validation remains available for releases or transfer, but it is no
longer the local execution environment:

```bash
make release-check
```

That target is an artifact audit only and does not install commands into the
active conda environment.

## Environment setup example

```bash
conda create -n se python=3.12 numpy pytest setuptools wheel pip
conda activate se
make conda-sync
make conda-check
```

Do not set `PYTHONPATH=src` for normal runs after `conda-sync`; doing so can hide
an editable-install metadata or console-entry mismatch.
