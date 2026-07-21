# Implementation Manifest

Version: 0.3.0

| Path | Bytes | SHA-256 |
|---|---:|---|
| `.gitignore` | 76 | `7e131d050c3b5bd39ea4b8db107dd7f4dc9cbebb2f9372bc2c5318abc5451cc9` |
| `CHANGELOG.md` | 1462 | `b0b31769ebc4a465583c0375deaa24943094adf3b49b87fe4ff59eb033d0d12e` |
| `README.md` | 6117 | `eabdd6c7404f84148171be4fb29b4b8f825a6e102f82d88463ac620b467760ba` |
| `configs/mvp_100k.json` | 1469 | `e05863718a2f010c659bd951001c74f4a93f427d9a74be820003616264df43f5` |
| `configs/mvp_small.json` | 1447 | `cbad4f59fda2562a3161df7f0dc8d56b92d104aea99c0811f6a2c3478671794d` |
| `docs/IMPLEMENTATION_STATUS.md` | 3308 | `7f6a9b218bd64f9de62c7c26fb65865ad15b3dddfa3d7403bc482bacff7a4574` |
| `docs/GPU_FOUNDATION.md` | 3206 | `3679fef48c7b60c265d1d0d95d568c9cf7b26c7f4dcf1f254dd3f73944cb8728` |
| `docs/NEXT_GPU_PHASE.md` | 1072 | `7e7ed9408edb77e4afbc3fe1b063bdfa8fb638da1b22784c3391d18659085334` |
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
| `pyproject.toml` | 612 | `cf36b3bd4ecf6aec10611a87b424ec1daa1a0a29fa2fae5d0f036a05dc5218d2` |
| `requirements.txt` | 12 | `a83a2a4ed7ab2e022b9b8a83cfa2b8cf52cc243006c597e8b96f90a8365590ac` |
| `scripts/run_demo.sh` | 173 | `56a4f91d2a74aadbd66116e0a6c202a82bc022c78fc2ec08fc1297ba24482b88` |
| `scripts/run_sweep.py` | 2385 | `8147a863939b7c5bc17133dcae8f1aa06c008168a841b4de1a0f142428e744bd` |
| `scripts/verify_gpu_foundation.py` | 5264 | `192ea2dcb51f454cd899619fcbcf5a27456aa8313678035a2878e9e633e34ca7` |
| `src/subject_evolution/__init__.py` | 302 | `72edab79b13fb48868ba06f2178b5b02f07cd10be739a4c561f8b13dad240a62` |
| `src/subject_evolution/__main__.py` | 30 | `6d8b7d7846a845059d7a3107143f11131f63c5511d669b44085b15ec5e3d2279` |
| `src/subject_evolution/backend.py` | 7339 | `1a59b129e4f97fa97e5c389e9ae4d7aa814dad9a2f5fa6a5e5b42869e2eca6e2` |
| `src/subject_evolution/cli.py` | 1300 | `2d704c8edb1a14f8feba5304495d1d1c0acb6786d7b9954695ea5336cc54667e` |
| `src/subject_evolution/config.py` | 5637 | `23b02983365a0e49bbaedc66cb8582fda08e4cdcae2b96382e707c2496abf315` |
| `src/subject_evolution/counterfactual.py` | 1878 | `01060d25ed613e43a07d1c0d4f7a3cbe18828e87f6059ad00a7b1c186baf9c7c` |
| `src/subject_evolution/environment.py` | 5340 | `23837a3e6e3bf90fcc84d77b2ca0ce8c9412480e30822f4e62db18f677604a55` |
| `src/subject_evolution/gpu_environment.py` | 9007 | `208a1fa9b041ab981ecc006b844c7dd6520b5100eb1625eb9a108e42f8ab8ee7` |
| `src/subject_evolution/information.py` | 14895 | `cca34313a2fe743217c8c65a873fb794fb2113af15c23e328e09ebd1fead833b` |
| `src/subject_evolution/intents.py` | 2749 | `8726cebcebc88e64fda0dfd2c62083302c22958f6fba3503e975cc7eedae4b1d` |
| `src/subject_evolution/metrics.py` | 1210 | `b273e3015c19025e0410071b47b916f06fca4973acc24cc5101a47ac90786c31` |
| `src/subject_evolution/policy.py` | 7052 | `5815a20df8aaf1263cd58e885f690a8bc6f20aed7f0158bc22981d3c748d9d68` |
| `src/subject_evolution/random_api.py` | 6330 | `73a135983d969ad238f76309cc8eb5ba865e67829471dbf4b74a6db90a654fe7` |
| `src/subject_evolution/reductions.py` | 3636 | `e55f0b7d990bdcb7aba82f8d80952bd6b4810741d414ed6849092ca4112c8736` |
| `src/subject_evolution/simulation.py` | 34379 | `0912dbe36cd2a36adc4d3dc06e96459be2d87efa04ac13cdc4dc88abaa65ec9d` |
| `src/subject_evolution/subjects.py` | 6703 | `2adba9c361c5c8f79019dcf6f867c90659e445252e6681750d7520a780f68a2e` |
| `src/subject_evolution/social.py` | 6584 | `cc6cbe3a3c6af64e3078154d3b06d0d40351f9eaf49ae4d7594ef41e6d0e07e0` |
| `src/subject_evolution/spatial.py` | 6698 | `83fa9ac2cd1b697107b435d739a3312b4af4e4479931fa243032188eec4ff54b` |
| `tests/test_backend.py` | 2123 | `d8d467a96edc0d6c96a7eb46a204c9ff6c0da08dc738bca64e53661fcc2582a5` |
| `tests/test_gpu_environment.py` | 5920 | `5ac00af2af65fbb8512af582abc1d86ce61b3e4265adf200a105f755786d7101` |
| `tests/test_random_api.py` | 935 | `5f529806c2361e25533b6e1a80a4521b6d679dac647ce0940278809e22b055a3` |
| `tests/test_random_api_gpu.py` | 3978 | `92ca85538d8caed115ea78d06a3efdd9c9fe23c10add03c8298bffbd70e14ab8` |
| `tests/test_simulation.py` | 5494 | `a3b825295b70f5ad50c5c253f1f52a2964d0bbb81f6dbd88a7c81e5d050525d3` |
| `tests/test_spatial.py` | 4020 | `d3c873df317d8ad0f582830546c4a76ec897cb0299ae2834342c708aa7a0eaf5` |
