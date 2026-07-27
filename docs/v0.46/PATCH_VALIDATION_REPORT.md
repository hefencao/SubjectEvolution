# Corrected v0.45 → v0.46 patch validation

- clean v0.45 baseline: used
- `git apply --check`: passed
- actual application: passed
- fuzz or offset: none
- changed paths: 51
- post-application content comparison: 250/250 files identical
- post-application test suite: `213 passed, 1 skipped`
- isolated wheel validation: reported `passed: true`

This corrected patch supersedes the earlier unexecuted v0.46 candidate and applies directly to the released v0.45 package.
