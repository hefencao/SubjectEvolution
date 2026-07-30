# Conda editable workflow

Activate the intended environment and synchronize metadata once after updating
to v0.41 because a new console entry point was added:

```bash
conda activate <env>
make conda-sync
```

The editable install points directly to `src/se`; ordinary source edits do not
require reinstalling a wheel. Rerun `make conda-sync` only after changing
`pyproject.toml`, entry points, dependencies, version, package layout, checkout
path or conda environment.

Daily validation:

```bash
make test
```

Long-run or handoff validation:

```bash
make conda-check
```

v0.41 verifies six console scripts:

- `se`
- `se-multi`
- `se-gui`
- `se-d1-factorial`
- `se-d2-audit`
- `se-d2-assess`

Do not set `PYTHONPATH=src` in the normal conda workflow; doing so can hide stale
editable metadata or a console script that still targets another checkout.
