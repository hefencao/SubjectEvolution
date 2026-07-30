# v0.77 validation report

## Completed

- Version consistency: passed for `0.77.0`.
- Portable documentation validation: passed.
- Full test file set: 74 files, 374 passed and 2 GPU-conditional skips.
- Configuration validation: all 102 shipped JSON configurations loaded and passed `validate_config`.
- Editable install validation: passed from this checkout in the available Python venv, including 125 imported modules, all 40 console entries and an external two-tick CPU smoke.
- CPU/reference parity: 20 passed and 2 real-GPU cases skipped.
- Isolated distribution validation: sdist/wheel build, isolated installation, module import, entry-point checks and external smoke passed.

The aggregate `make test` runner was invoked but exceeded the container call limit under five-way process contention. The same deterministic 74-file partition was then completed in bounded invocations; no file was omitted.

## Environment-limited gates

- `make conda-sync` was invoked and stopped after version/bytecode checks because the Conda active-environment marker is unset.
- `make conda-check` was invoked but cannot complete its Conda-required editable branch in this non-Conda container.
- `make parity-gpu` was invoked and failed its required-device assertion because no usable CuPy/CUDA device is available. The failure occurred before any real-device numerical comparison.

These are execution-environment limitations, not recorded passes.

## Artifact verification

- The unified patch was applied with `patch -p1` to a fresh copy of the supplied v0.76 baseline. The resulting 361-file SHA-256 manifest exactly matched the clean v0.77 tree.
- The patch-replayed tree passed version consistency, portable-documentation checks, 28 focused governance/package tests and validation of all 102 shipped configurations.
- The clean project archive was re-extracted and rechecked. It contains 361 files and no cache, bytecode, build, distribution, validation, VCS or editable-install metadata.
