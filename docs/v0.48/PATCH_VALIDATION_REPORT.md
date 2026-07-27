# v0.47 → v0.48 patch validation

The patch was applied to a fresh extraction of `se_v047_project.zip`.

- `git apply --check`: passed
- actual application: passed
- fuzz or offset: none
- candidate and patched trees: 259/259 files hash-identical
- patched-tree tests: `223 passed, 1 skipped`
- patched-tree isolated sdist/wheel validation: passed

The final patch is regenerated after including this report and replayed again before delivery.
