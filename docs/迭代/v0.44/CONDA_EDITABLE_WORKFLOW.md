# Conda editable workflow

v0.44 changes version metadata and adds two console entries, so upgrade once with:

```bash
conda activate <your-env>
make conda-sync
```

Daily validation:

```bash
make test
make conda-check
```

`make conda-check` verifies the exact editable checkout, version `0.44.0`, all importable modules, ten console entries and an external-directory smoke run. Wheel installation remains an optional release artifact audit, not the daily workflow.
