# Conda editable workflow

v0.43 adds the `se-d2-lineage-assess` console entry and changes package metadata. Run once after upgrading:

```bash
conda activate <your-env>
make conda-sync
```

Routine validation remains:

```bash
make test
make conda-check
```

Do not install the wheel as the normal development workflow and do not set `PYTHONPATH=src` inside the activated editable environment.
