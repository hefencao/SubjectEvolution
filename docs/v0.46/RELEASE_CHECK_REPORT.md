# v0.46 corrected release check

Command:

```bash
CONDA_PREFIX=/opt/pyvenv make release-check
```

Result:

- source test: `213 passed, 1 skipped`
- isolated sdist/wheel audit: passed
- isolated wheel: `se_mvp-0.46.0-py3-none-any.whl`
- disposable environment validation: passed

The wheel is used only as an artifact audit. Conda plus editable install remains the normal local workflow.
