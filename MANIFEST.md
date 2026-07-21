# Implementation Manifest

Version: 0.2.0

| Path | Bytes | SHA-256 |
|---|---:|---|
| `.gitignore` | 76 | `7e131d050c3b5bd39ea4b8db107dd7f4dc9cbebb2f9372bc2c5318abc5451cc9` |
| `CHANGELOG.md` | 926 | `8a380b1430283b7ab349aa4835a20f51e6de9f9a01c93f141a6af45b40448b4b` |
| `README.md` | 4452 | `8a7d1811f44f87f16963a47378769c1f26af10e935be15add622e915f17eb650` |
| `configs/mvp_100k.json` | 1469 | `e05863718a2f010c659bd951001c74f4a93f427d9a74be820003616264df43f5` |
| `configs/mvp_small.json` | 1447 | `cbad4f59fda2562a3161df7f0dc8d56b92d104aea99c0811f6a2c3478671794d` |
| `docs/IMPLEMENTATION_STATUS.md` | 2878 | `ce48cfe0eba05fcfbe0131dba2626f734042fae7f460a5b1c783fea9397515d9` |
| `docs/NEXT_GPU_PHASE.md` | 927 | `9f36af5aaa7d729a59bb18db6178b6a738e496be2695f379d4fba3e6f760b6a0` |
| `docs/specification/00_master_project_spec.md` | 12255 | `85de7648f965f7689a59ddf2143aa273e3b8e1b8f568adafaab0609dc2391392` |
| `docs/specification/01_data_structure_spec.md` | 10293 | `5c3d597a6afa23f97a3f7fe257c6c84119603220bf74f12a4782c44582688cbc` |
| `docs/specification/02_gpu_execution_pipeline.md` | 9538 | `cdb1a54ce40c0e0f56ed7163048b46c0a9abd8db14d828e7eb3ad25b3743e80f` |
| `docs/specification/03_unified_sampling_api.md` | 10011 | `408d1498ceada54dca5cf52ca9b8480bb0981eaefc281d09c1ea472fb6a273d8` |
| `docs/specification/04_mvp_experiment_config.md` | 11877 | `451a944a4554b9db5b4124fcfc2728d4681777f5a897ea0990742608192c51e7` |
| `docs/specification/MANIFEST.md` | 867 | `257161790feb4e2bcd32af4a5d9776b2cc4cdd2e0e4af74e3530737562bc0ca2` |
| `docs/specification/README.md` | 2111 | `acc5632e192deeb627413569918f4e768f2d5a6c7a1df1e131704295117ef495` |
| `examples/demo_200/config.json` | 1109 | `bb584f9052f781c1bde32f3f3defdd42c5abc542156577aeba366ee0ecb54fca` |
| `examples/demo_200/metrics.csv` | 3159 | `a29e2c8b0213a3a79680aebb2e89729582397f0a84946ef681a20a64cf35bce3` |
| `examples/demo_200/run_metadata.json` | 1092 | `03c0359baadbd068561a920446eb1c2eddce31510b6fd3ff1af741bd58cd8e78` |
| `examples/demo_200/summary.json` | 735 | `53e89298f6e5e95a0d7903cc50fa0d4097079ebe8ec69e2ad9a5bca9b0bafc06` |
| `pyproject.toml` | 612 | `e002510e0880809e0e26dea9cb294d452c5e68937c36961e7b0081fa03848bad` |
| `requirements.txt` | 12 | `a83a2a4ed7ab2e022b9b8a83cfa2b8cf52cc243006c597e8b96f90a8365590ac` |
| `scripts/run_demo.sh` | 173 | `56a4f91d2a74aadbd66116e0a6c202a82bc022c78fc2ec08fc1297ba24482b88` |
| `scripts/run_sweep.py` | 2385 | `8147a863939b7c5bc17133dcae8f1aa06c008168a841b4de1a0f142428e744bd` |
| `src/subject_evolution/__init__.py` | 90 | `0aa95e09abc01fc65803681f4ca91395775afda98a85002943f8729101fab558` |
| `src/subject_evolution/__main__.py` | 30 | `6d8b7d7846a845059d7a3107143f11131f63c5511d669b44085b15ec5e3d2279` |
| `src/subject_evolution/cli.py` | 1300 | `2d704c8edb1a14f8feba5304495d1d1c0acb6786d7b9954695ea5336cc54667e` |
| `src/subject_evolution/config.py` | 5637 | `23b02983365a0e49bbaedc66cb8582fda08e4cdcae2b96382e707c2496abf315` |
| `src/subject_evolution/counterfactual.py` | 1878 | `01060d25ed613e43a07d1c0d4f7a3cbe18828e87f6059ad00a7b1c186baf9c7c` |
| `src/subject_evolution/environment.py` | 4749 | `4962510b796d464349097792c0e8bbd2541a9af8a52ec9ff37272e51a4b85fbc` |
| `src/subject_evolution/information.py` | 14445 | `05bd5ad8686ddc7f7a79bd01f3675edba5b795b2a7076575f70e2bccf2fad0f8` |
| `src/subject_evolution/intents.py` | 2749 | `8726cebcebc88e64fda0dfd2c62083302c22958f6fba3503e975cc7eedae4b1d` |
| `src/subject_evolution/metrics.py` | 1210 | `b273e3015c19025e0410071b47b916f06fca4973acc24cc5101a47ac90786c31` |
| `src/subject_evolution/policy.py` | 7052 | `5815a20df8aaf1263cd58e885f690a8bc6f20aed7f0158bc22981d3c748d9d68` |
| `src/subject_evolution/random_api.py` | 4393 | `3fbaee52ab2c48488ec023c909d985e4396d9623686ffffa6945a163a30f9843` |
| `src/subject_evolution/simulation.py` | 34349 | `7fd29d1b22526fab3ea6d4afacfcb7252e11a47d59d1b76a9f8184bb03979983` |
| `src/subject_evolution/subjects.py` | 6703 | `2adba9c361c5c8f79019dcf6f867c90659e445252e6681750d7520a780f68a2e` |
| `src/subject_evolution/social.py` | 6584 | `cc6cbe3a3c6af64e3078154d3b06d0d40351f9eaf49ae4d7594ef41e6d0e07e0` |
| `src/subject_evolution/spatial.py` | 4181 | `e10482175b330e286c1087902c55dd3dd741fbac7615701e0472f95ca4778ad0` |
| `tests/test_random_api.py` | 935 | `5f529806c2361e25533b6e1a80a4521b6d679dac647ce0940278809e22b055a3` |
| `tests/test_simulation.py` | 5159 | `84f82e4527e6a8a1c40e93c58c27247913e151e5a107f91b3fb5ecd98ed4de5f` |
