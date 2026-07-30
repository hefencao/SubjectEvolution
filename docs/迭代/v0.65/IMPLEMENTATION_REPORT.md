# v0.65 implementation report

## Scope

v0.65 advances the large-population hybrid GPU execution path. It does not add or modify any world, reward, sensing, inheritance, population-support or ecological mechanism.

The supplied audit already establishes that 128/128 D3-I branches used real `gpu-hybrid-accelerated` execution with no fallback. Their late 100–300 alive windows are not treated as a throughput gate; small batches are expected to be dominated by launch, transfer and remaining CPU settlement overhead.

## Device-resident work

The following regular observation inputs are now produced from persistent device state:

- normalized fixed-budget resource affinity;
- normalized fixed-budget direct/trace danger evidence;
- storage-conditioned policy resource utility;
- oxygen, terrain and wear field updates;
- oxygen gradients;
- information detection summaries on non-diagnostic ticks.

Full information observation arrays remain available at parity and evaluation boundaries. The runtime records actual H2D/D2H bytes and separately reports the semantic host payload avoided.

Independent latent roots created by knowledge outcomes now defer materialization
until the canonical commit loop completes. SplitMix64 root, action, context and
outcome-projection hash components are generated as exact uint64 GPU batches.
CPU commit order, floating accumulation and int16 quantization are unchanged.
The runtime reports the batch as `gpu_device_latent_root_rows` and includes its
actual transfers in H2D/D2H telemetry.

## Deferred-sync correction

Long `Simulation.run()` calls intentionally defer full GPU-to-host environment synchronization. Previously, local physiology and terrain settlement could still read the stale CPU mirror even though the current fields were device authoritative. v0.65 retrieves active-cell physiology directly from the device and materializes complete physiology fields only for metrics/checkpoints. This changes no modeled equation; it restores the intended current-tick semantics of the hybrid route.

## Large-run presets

- `mvp_d3i_gpu_scale4_longrun.json`: 8,000 initial entities, 32,768 capacity, 512×512 world, 128×128 grid, 3,000 ticks.
- `mvp_d3i_gpu_scale8_longrun.json`: 32,000 initial entities, 131,072 capacity, 1,024×1,024 world, 256×256 grid, 1,500 ticks.

Both preserve entity density and per-cell mechanism parameters, request hybrid acceleration through `auto`, and disable per-tick invariant validation. They do not bypass target-device parity.

Both now write observation and trusted full-world checkpoints every 100 ticks.
The cadence changes recovery granularity only: it does not select seeds, rescue
populations or imply that any checkpoint has adequate evolutionary turnover.

## Validation boundary

The local `se` Conda environment exposes CuPy 14.1.1 and an NVIDIA GeForce RTX
4070. The direct required-device suite therefore validates real CUDA here.
An archival `make parity-gpu` certificate remains a separate release artifact;
passing an interactive pytest command is not represented as that certificate.

## Completed validation

- JSON configurations: 95/95 load successfully.
- Python compilation: 191 files.
- Full deterministic shards: 318 passed, 2 skipped; the sandboxed shard process cannot access the device.
- Real required-device parity in `se`: 22 passed with no skip.
- Exact CPU versus device-batched latent catalog arrays cover length, offset, values and encoded bytes.
- A scale-4 tick-100 run wrote a 19 MiB `.npz` and 36 MiB `.sechk`; the bundle checksum passed and a real-GPU resume advanced from tick 100 to 101.
- Matched 20-tick cProfile: 22.9 s before versus 14.0 s after latent hash migration. Non-profiler scale-4 100-tick window: 0.4098 s/tick versus the prior 0.4211 s/tick baseline.
- Non-Conda editable verification: 117 modules and 32 console entries, with external empty-`PYTHONPATH` smoke.
- Isolated wheel and sdist release validation passed.
