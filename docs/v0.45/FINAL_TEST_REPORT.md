# v0.45 final test report

- baseline v0.44: `208 passed, 1 skipped`
- candidate v0.45 targeted D2-G tests: `3 passed`
- candidate v0.45 full test suite: `211 passed, 1 skipped`
- `make conda-check`: passed
- installed editable version: `0.45.0`
- importable modules: `89`
- console entries: `12`
- external-directory CPU smoke: passed
- JSON configurations: `75/75`
- Python source/test/script files compiled: `135/135`
- installed real-input D2-G plan: byte-identical to the preregistered project copy
- installed D2-G plan → execute → assess smoke: passed
- ordinary-run v0.44/v0.45 checkpoint state SHA-256: identical
- ordinary-run non-timing metrics differences: `0`

The new source-population logic is reached only through the explicit D2-G runner. Ordinary simulation initialization and world logic remain unchanged.
