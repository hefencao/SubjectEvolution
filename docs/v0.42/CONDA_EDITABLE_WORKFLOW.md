# Conda editable workflow

v0.42 adds the `se-d2-lineage-pairs` console entry and changes package metadata.
Run once after upgrading:

```bash
conda activate <your-env>
make conda-sync
```

Normal source iteration:

```bash
make test
```

Before long runs or delivery:

```bash
make conda-check
```

The verification rejects stale editable metadata, a checkout mismatch, stale
console entries, external import failures and a failed clean-directory smoke run.
