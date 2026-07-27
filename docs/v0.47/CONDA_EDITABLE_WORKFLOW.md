# Conda editable workflow

After upgrading to v0.47, synchronize once because version metadata and console entries changed:

```bash
conda activate <your-env>
make conda-sync
```

Normal validation:

```bash
make test
make conda-check
```

`make conda-check` verifies the active Conda prefix, editable source root, package version, importable modules, console entries and an external-directory smoke run.

Artifact-only validation:

```bash
make release-check
```

Do not install a wheel as the normal development workflow.
