# Implementation Manifest

Version: 0.1.0

| Path | Bytes | SHA-256 |
|---|---:|---|
| `.gitignore` | 76 | `7e131d050c3b5bd39ea4b8db107dd7f4dc9cbebb2f9372bc2c5318abc5451cc9` |
| `CHANGELOG.md` | 422 | `1258aafa8f8246633ae81211adec6ef71b2d8df24d2f45efe984ae1e4f2a8b91` |
| `README.md` | 3695 | `5cc68b3b09b0a3371dcab315d3ab70701a54b6364255e3c09610dea92f5d535c` |
| `configs/mvp_100k.json` | 1408 | `a3153ad1a25c66e22a67abd99419a759c8dc7880d1d8232ff8e58f339a08989f` |
| `configs/mvp_small.json` | 1386 | `9ce4d099731f323b3630131934305e3501044bcbcf7dc26e9038a2a019d592ec` |
| `docs/IMPLEMENTATION_STATUS.md` | 2638 | `178cea7eb9096dec5758733787acd65dd6e396b030f805b9b9b516ffdf4fcbae` |
| `docs/NEXT_GPU_PHASE.md` | 690 | `2b48dfb1362631219d944fda81c00ca68c084133d1dc62d273b8f78875eebb2e` |
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
| `pyproject.toml` | 612 | `e2ba304c738c0334e321d68e326f0be2ff453f2d017a18a78c74ff5422a9b78d` |
| `requirements.txt` | 12 | `a83a2a4ed7ab2e022b9b8a83cfa2b8cf52cc243006c597e8b96f90a8365590ac` |
| `scripts/run_demo.sh` | 173 | `56a4f91d2a74aadbd66116e0a6c202a82bc022c78fc2ec08fc1297ba24482b88` |
| `scripts/run_sweep.py` | 2385 | `8147a863939b7c5bc17133dcae8f1aa06c008168a841b4de1a0f142428e744bd` |
| `src/subject_evolution/__init__.py` | 90 | `c70a9d8924c889b6dbbf1ca2e8890024d103fccf8aedab13ac3cc850cc8f275b` |
| `src/subject_evolution/__main__.py` | 30 | `6d8b7d7846a845059d7a3107143f11131f63c5511d669b44085b15ec5e3d2279` |
| `src/subject_evolution/cli.py` | 849 | `dc85f8e6d406ff6bfdcca1c52155b41ae59df205bfe6438916d07e97c55809a2` |
| `src/subject_evolution/config.py` | 4769 | `07dffd2dae2ab441029454a58349e7f23e2a219348e21f7058143ed26cda69be` |
| `src/subject_evolution/environment.py` | 4077 | `d96d50cc037172ebe0dcb2e4dabec20e61f8c10b89e07ed3c8378781592c269e` |
| `src/subject_evolution/information.py` | 5990 | `fcb5e6ec295bd66e3e4dfc73d0327af8bcf16c9d8db06a48752c6bf6422fcee3` |
| `src/subject_evolution/metrics.py` | 1210 | `b273e3015c19025e0410071b47b916f06fca4973acc24cc5101a47ac90786c31` |
| `src/subject_evolution/policy.py` | 7052 | `5815a20df8aaf1263cd58e885f690a8bc6f20aed7f0158bc22981d3c748d9d68` |
| `src/subject_evolution/random_api.py` | 4393 | `3fbaee52ab2c48488ec023c909d985e4396d9623686ffffa6945a163a30f9843` |
| `src/subject_evolution/simulation.py` | 21068 | `4a528a444a2be4e4e049ff80ce9eec9ec70b32eacc225a27c67b0556878c1e55` |
| `src/subject_evolution/social.py` | 6584 | `cc6cbe3a3c6af64e3078154d3b06d0d40351f9eaf49ae4d7594ef41e6d0e07e0` |
| `src/subject_evolution/spatial.py` | 4181 | `e10482175b330e286c1087902c55dd3dd741fbac7615701e0472f95ca4778ad0` |
| `tests/test_random_api.py` | 935 | `5f529806c2361e25533b6e1a80a4521b6d679dac647ce0940278809e22b055a3` |
| `tests/test_simulation.py` | 2607 | `733a3701316fcd0db3848a2325ce57be81edb6bcd69be6418a201f7f4d848b20` |
