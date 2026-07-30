# v0.44 Conda editable check transcript

Command: `CONDA_PREFIX=/opt/pyvenv make conda-check`

```text
python -m pip install --no-deps --no-build-isolation -e .
Looking in indexes: https://reader:****@packages.applied-caas-gateway1.internal.api.openai.org/artifactory/api/pypi/pypi-public/simple
Obtaining file:///mnt/data/work_v043/se_v043_project
  Checking if build backend supports build_editable: started
  Checking if build backend supports build_editable: finished with status 'done'
  Preparing editable metadata (pyproject.toml): started
  Preparing editable metadata (pyproject.toml): finished with status 'done'
Building wheels for collected packages: se-mvp
  Building editable for se-mvp (pyproject.toml): started
  Building editable for se-mvp (pyproject.toml): finished with status 'done'
  Created wheel for se-mvp: filename=se_mvp-0.44.0-0.editable-py3-none-any.whl size=4131 sha256=a4af73c8e54a4652e29b684f28ac9b1375b8225da15dbd232a39ab3d1c205194
  Stored in directory: /tmp/pip-ephem-wheel-cache-y6j5kugk/wheels/9a/02/3e/471e506ef5c387f83498700788f1649a9870007e8c7a7f8fa2
Successfully built se-mvp
Installing collected packages: se-mvp
  Attempting uninstall: se-mvp
    Found existing installation: se-mvp 0.44.0
    Uninstalling se-mvp-0.44.0:
      Successfully uninstalled se-mvp-0.44.0
Successfully installed se-mvp-0.44.0
python scripts/verify_conda_editable.py --project . --require-conda
{"passed": true, "project": "/mnt/data/work_v043/se_v043_project", "python": "/opt/pyvenv/bin/python", "conda_prefix": "/opt/pyvenv", "version": "0.44.0", "package_path": "/mnt/data/work_v043/se_v043_project/src/se/__init__.py", "editable_root": "/mnt/data/work_v043/se_v043_project", "module_count": 87, "entry_points": {"se": "se.cmd.run:main", "se-d1-factorial": "se.experiments.d1_factorial:main", "se-d2-assess": "se.analysis.d2_effects:main", "se-d2-audit": "se.experiments.d2_module_audit:main", "se-d2-lineage-assess": "se.analysis.d2_lineage_effects:main", "se-d2-lineage-mediate": "se.experiments.d2_lineage_mediation:main", "se-d2-lineage-mediate-assess": "se.analysis.d2_lineage_mediation_effects:main", "se-d2-lineage-pairs": "se.experiments.d2_lineage_pairs:main", "se-gui": "se.gui.runner:main", "se-multi": "se.cmd.multi_seed:main"}, "smoke": null}
python -m pytest -q
........................................................................ [ 34%]
........................................................................ [ 68%]
..............................s..................................        [100%]
208 passed, 1 skipped in 24.43s
python scripts/verify_conda_editable.py --project . --require-conda --smoke --report docs/v0.44/CONDA_EDITABLE_VALIDATION_REPORT.json
{"passed": true, "project": "/mnt/data/work_v043/se_v043_project", "python": "/opt/pyvenv/bin/python", "conda_prefix": "/opt/pyvenv", "version": "0.44.0", "package_path": "/mnt/data/work_v043/se_v043_project/src/se/__init__.py", "editable_root": "/mnt/data/work_v043/se_v043_project", "module_count": 87, "entry_points": {"se": "se.cmd.run:main", "se-d1-factorial": "se.experiments.d1_factorial:main", "se-d2-assess": "se.analysis.d2_effects:main", "se-d2-audit": "se.experiments.d2_module_audit:main", "se-d2-lineage-assess": "se.analysis.d2_lineage_effects:main", "se-d2-lineage-mediate": "se.experiments.d2_lineage_mediation:main", "se-d2-lineage-mediate-assess": "se.analysis.d2_lineage_mediation_effects:main", "se-d2-lineage-pairs": "se.experiments.d2_lineage_pairs:main", "se-gui": "se.gui.runner:main", "se-multi": "se.cmd.multi_seed:main"}, "smoke": {"command": ["/opt/pyvenv/bin/python", "-m", "se", "--config", "/tmp/se-conda-smoke-utdhaqd1/smoke.json", "--output", "/tmp/se-conda-smoke-utdhaqd1/run", "--backend", "cpu", "--until-tick", "2"], "output_exists": true, "stdout_tail": ["tick=      1 alive=    200 groups=    0 E=1.785 step=0.096s window_avg=0.096s wall=0.1s", "tick=      2 alive=    200 groups=    0 E=1.774 step=0.105s window_avg=0.107s wall=0.2s"]}}
```
