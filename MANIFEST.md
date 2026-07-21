# Implementation Manifest

Version: 0.4.0

| Path | Bytes | SHA-256 |
|---|---:|---|
| `.gitignore` | 76 | `7e131d050c3b5bd39ea4b8db107dd7f4dc9cbebb2f9372bc2c5318abc5451cc9` |
| `CHANGELOG.md` | 2104 | `241ee08ea50c79931e5bd14f3f55e76536da49f72dbbe47a8b068b2ce8d99b72` |
| `README.md` | 6856 | `824f883bddc068309c166b30e1cd69c2490bc462f9924d58bdcf675cf797252d` |
| `configs/mvp_100k.json` | 1469 | `e05863718a2f010c659bd951001c74f4a93f427d9a74be820003616264df43f5` |
| `configs/mvp_small.json` | 1447 | `cbad4f59fda2562a3161df7f0dc8d56b92d104aea99c0811f6a2c3478671794d` |
| `docs/IMPLEMENTATION_STATUS.md` | 3829 | `c72aa231af622d640e464a820746fe9c2386cf173bb90e3704b971ae183d7dbe` |
| `docs/GPU_FOUNDATION.md` | 4537 | `352b327915955ca3e17bc08fdada3e27f330e1574c64d902d17d1dc59621a259` |
| `docs/NEXT_GPU_PHASE.md` | 1194 | `a69dbbc6780494d6e5277bc2e43cf15c7bd1e89bd06ad2d1fe0ff51e6fc14ddb` |
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
| `pyproject.toml` | 612 | `d1e6bb83af9f625964d76e5fe9b175208cc1197bac93599a29fe60f640494b61` |
| `requirements.txt` | 12 | `a83a2a4ed7ab2e022b9b8a83cfa2b8cf52cc243006c597e8b96f90a8365590ac` |
| `scripts/run_demo.sh` | 173 | `56a4f91d2a74aadbd66116e0a6c202a82bc022c78fc2ec08fc1297ba24482b88` |
| `scripts/run_sweep.py` | 2385 | `8147a863939b7c5bc17133dcae8f1aa06c008168a841b4de1a0f142428e744bd` |
| `scripts/verify_gpu_foundation.py` | 5264 | `192ea2dcb51f454cd899619fcbcf5a27456aa8313678035a2878e9e633e34ca7` |
| `src/subject_evolution/__init__.py` | 302 | `1b81e0af0ba7edf7c19d03fe8a8b5f55f4e7b4cb04ec75072dce9404acc063a0` |
| `src/subject_evolution/__main__.py` | 30 | `6d8b7d7846a845059d7a3107143f11131f63c5511d669b44085b15ec5e3d2279` |
| `src/subject_evolution/backend.py` | 7339 | `1a59b129e4f97fa97e5c389e9ae4d7aa814dad9a2f5fa6a5e5b42869e2eca6e2` |
| `src/subject_evolution/cli.py` | 1565 | `89c49e684101c07174ea106c54f28dff3a5644dbdf713772f1b740005dceddd3` |
| `src/subject_evolution/config.py` | 5637 | `23b02983365a0e49bbaedc66cb8582fda08e4cdcae2b96382e707c2496abf315` |
| `src/subject_evolution/counterfactual.py` | 1878 | `01060d25ed613e43a07d1c0d4f7a3cbe18828e87f6059ad00a7b1c186baf9c7c` |
| `src/subject_evolution/environment.py` | 5340 | `23837a3e6e3bf90fcc84d77b2ca0ce8c9412480e30822f4e62db18f677604a55` |
| `src/subject_evolution/gpu_environment.py` | 15223 | `abe69cb428365432cc89a40a784f032c6fffa32449d5f2dba6ba4f88947d9bc3` |
| `src/subject_evolution/gpu_runtime.py` | 14734 | `673a21d69741052ae1e9fc6dbf25104c496fe62644db7d6621c1d409b37b8916` |
| `src/subject_evolution/information.py` | 17286 | `c109fdc1f383f96ea3f00c9c20f778e5978c4edde617d17a44d5276909108d24` |
| `src/subject_evolution/intents.py` | 2749 | `8726cebcebc88e64fda0dfd2c62083302c22958f6fba3503e975cc7eedae4b1d` |
| `src/subject_evolution/metrics.py` | 1210 | `b273e3015c19025e0410071b47b916f06fca4973acc24cc5101a47ac90786c31` |
| `src/subject_evolution/policy.py` | 7184 | `2e60edd8e616ed36d2106d069b800d1d7c4eb1c6aff1d2a6e87204f68b19e457` |
| `src/subject_evolution/random_api.py` | 6947 | `a92b8c6928de3d93a0b112601e93ea9dfd1c39fddea5202c492d940dd385acec` |
| `src/subject_evolution/reductions.py` | 3636 | `e55f0b7d990bdcb7aba82f8d80952bd6b4810741d414ed6849092ca4112c8736` |
| `src/subject_evolution/simulation.py` | 39344 | `6ea6509ba32227ab40e6861b9e2e82e57566c998c4a28a2b88b0e36a41b617cb` |
| `src/subject_evolution/subjects.py` | 6703 | `2adba9c361c5c8f79019dcf6f867c90659e445252e6681750d7520a780f68a2e` |
| `src/subject_evolution/social.py` | 6584 | `cc6cbe3a3c6af64e3078154d3b06d0d40351f9eaf49ae4d7594ef41e6d0e07e0` |
| `src/subject_evolution/spatial.py` | 6698 | `83fa9ac2cd1b697107b435d739a3312b4af4e4479931fa243032188eec4ff54b` |
| `tests/test_backend.py` | 2123 | `d8d467a96edc0d6c96a7eb46a204c9ff6c0da08dc738bca64e53661fcc2582a5` |
| `tests/test_gpu_environment.py` | 5920 | `5ac00af2af65fbb8512af582abc1d86ce61b3e4265adf200a105f755786d7101` |
| `tests/test_gpu_runtime.py` | 1658 | `880ae5adea76e4b3cfbd3ed2e0094c2ce1bbc90805bfdb97f8111c30024d98de` |
| `tests/test_random_api.py` | 1770 | `7883c0ec5caaa9e7a22a1ba1a807cf7d492277111505bb0f7a8ed892fec4bce6` |
| `tests/test_random_api_gpu.py` | 4545 | `61817c238b4168e6c69defb5453c4b20d838d8e76232f076af527ae67a8732d5` |
| `tests/test_simulation.py` | 7081 | `0b7b7b853f0231956c58c6e1f57f60262295bddda0ecbbce03433addf96766b4` |
| `tests/test_spatial.py` | 4020 | `d3c873df317d8ad0f582830546c4a76ec897cb0299ae2834342c708aa7a0eaf5` |
