# v0.44 release artifact audit

Command: `make release-check`

```text
PYTHONPATH=src python -m pytest -q
........................................................................ [ 34%]
........................................................................ [ 68%]
..............................s..................................        [100%]
208 passed, 1 skipped in 22.40s
python scripts/verify_dist.py --project .
{"passed": true, "report": "/tmp/se-dist-verify-_rpj_bo3/isolated_wheel_validation.json", "wheel": "/tmp/se-dist-verify-_rpj_bo3/dist/wheel/se_mvp-0.44.0-py3-none-any.whl", "venv": "/tmp/se-dist-verify-_rpj_bo3/venv"}
release-check is an artifact audit only; conda-sync is the local runtime workflow.
```
