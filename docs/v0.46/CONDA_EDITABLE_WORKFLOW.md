# Conda editable workflow

v0.46 changes version metadata and adds two console entries, so run once after upgrading:

```bash
conda activate <your-env>
make conda-sync
```

Routine validation:

```bash
make test
make conda-check
```

Do not install the wheel as the normal development workflow. The release artifact checks remain isolated verification only.
