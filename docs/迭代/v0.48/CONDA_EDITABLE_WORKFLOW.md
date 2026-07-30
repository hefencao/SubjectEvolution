# Conda editable workflow

v0.48 changes package metadata and adds `se-d2-compose`; after upgrading run once:

```bash
conda activate <environment>
make conda-sync
```

Routine validation:

```bash
make test
make conda-check
```

`make release-check` remains an isolated packaging audit, not the daily installation workflow.
