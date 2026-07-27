# v0.44 → v0.45 patch validation

- changed paths: `111`
- `git apply --check`: passed
- actual application on a clean v0.44 extraction: passed
- fuzz/offset: none
- candidate/patched tree comparison: `250/250` files exact
- patched tree tests: `211 passed, 1 skipped`
- patched tree isolated sdist/wheel validation: passed

The report is included in the final patch and the final patch was replayed once more from a fresh baseline.
