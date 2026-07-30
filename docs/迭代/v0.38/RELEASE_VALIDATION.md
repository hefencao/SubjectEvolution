# Isolated distribution validation

## Why reinstalling in one shared environment is insufficient

A shared environment can retain an older editable install, stale package files,
user-site packages or a working-directory path that shadows the installed
wheel. Running tests from the repository also intentionally places `src` on the
Python path, so those tests do not prove that the artifact is complete.

## Required release check

```bash
make release-check PREVIOUS_WHEEL=/path/to/previous.whl
```

The distribution verifier performs the following in a disposable workspace:

1. build an sdist from the source tree;
2. build the wheel from that sdist;
3. create a fresh venv;
4. optionally install the previous wheel;
5. install the candidate with `--force-reinstall --no-deps`;
6. set `PYTHONPATH` empty and disable user site;
7. execute outside the source tree;
8. verify metadata version, package version and `se.__file__` origin;
9. import every installed `se.*` module;
10. run `pip check`;
11. run all four console-script help paths;
12. copy a config outside the repository and execute a short simulation.

The default offline-friendly mode uses system site packages only for already
available dependencies such as NumPy, while still proving that `se` comes from
the disposable venv. Strict mode creates a venv without system site packages and
installs dependencies from an explicit wheelhouse:

```bash
python scripts/verify_dist.py \
  --project . \
  --strict \
  --wheelhouse /path/to/wheelhouse
```

A release is incomplete if this check is not run after the final source and
document changes.
