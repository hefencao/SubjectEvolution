# v0.45 release artifact validation

The two components of `make release-check` were executed successfully:

1. `PYTHONPATH=src python -m pytest -q`: `211 passed, 1 skipped`.
2. `python scripts/verify_dist.py --project .`: passed; an sdist was built, converted to a wheel, installed in a disposable virtual environment and validated there.

A combined `make release-check` invocation was also attempted. The execution host terminated the second, repeated isolated-build step after the test phase; no assertion or artifact-validation failure was reported. The same `verify_dist.py` command completed successfully when executed independently and is the authoritative artifact result recorded here.
