# Conda editable workflow

v0.45 changes project version metadata and adds two console entries, so run once after upgrading:

```bash
conda activate <your-env>
make conda-sync
```

Normal source edits then remain visible through the editable install. Routine validation:

```bash
make test
make conda-check
```
