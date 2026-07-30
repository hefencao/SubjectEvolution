# v0.47 release artifact audit

`CONDA_PREFIX=/opt/pyvenv make release-check` completed successfully.

- source-tree tests: **218 passed, 1 skipped**;
- isolated sdist build: passed;
- wheel built from the sdist: `se_mvp-0.47.0-py3-none-any.whl`;
- disposable virtual-environment validation: passed.

The artifact audit is separate from the normal Conda editable workflow.
