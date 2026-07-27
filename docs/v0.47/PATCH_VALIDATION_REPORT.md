# v0.46 -> v0.47 patch validation

The preliminary patch was applied to a fresh extraction of the corrected v0.46 package.

- `git apply --check`: passed
- actual application: passed
- fuzz/offset: none
- candidate/applied content: 252/252 files identical
- patch-tree pytest: **218 passed, 1 skipped**
- patch-tree isolated sdist/wheel audit: passed

The final patch is regenerated after adding this record and validated once more from a fresh baseline.
