# v0.62 Conda validation status

- active Conda environment: `False`
- `CONDA_PREFIX`: `None`
- `make conda-sync`: attempted; expected environment-guard failure
- `make conda-check`: all 291 tests passed with 1 skipped before the expected Conda editable guard failure
- non-Conda editable validation: 116 modules, 31 console entries, external smoke passed
- isolated wheel/sdist release audit: passed

No `CONDA_PREFIX` was fabricated. Activate the intended local environment and run:

```bash
make conda-sync
make test
make conda-check
```
