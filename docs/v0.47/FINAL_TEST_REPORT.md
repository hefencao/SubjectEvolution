# v0.47 final test report

Commands executed from the editable checkout:

```bash
make test
CONDA_PREFIX=/opt/pyvenv make conda-check
CONDA_PREFIX=/opt/pyvenv make release-check
```

Results:

- pytest: **218 passed, 1 skipped**;
- JSON configurations: **75 / 75** parsed;
- Python files under `src`, `scripts`, and `tests`: **141 / 141** compiled;
- editable import/version/entry verification: passed;
- external-directory 2-tick CPU smoke: passed;
- isolated sdist-to-wheel disposable-environment audit: passed.
