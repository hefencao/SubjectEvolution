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

## Deferred-sync correction

Long `Simulation.run()` calls intentionally defer full GPU-to-host environment synchronization. Previously, local physiology and terrain settlement could still read the stale CPU mirror even though the current fields were device authoritative. v0.65 retrieves active-cell physiology directly from the device and materializes complete physiology fields only for metrics/checkpoints. This changes no modeled equation; it restores the intended current-tick semantics of the hybrid route.

## Large-run presets

- `mvp_d3i_gpu_scale4_longrun.json`: 8,000 initial entities, 32,768 capacity, 512×512 world, 128×128 grid, 3,000 ticks.
- `mvp_d3i_gpu_scale8_longrun.json`: 32,000 initial entities, 131,072 capacity, 1,024×1,024 world, 256×256 grid, 1,500 ticks.

Both preserve entity density and per-cell mechanism parameters, request hybrid acceleration through `auto`, and disable per-tick invariant validation. They do not bypass target-device parity.

## Validation boundary

The local delivery environment has no usable CUDA/CuPy device. CPU/no-device tests and CPU-emulated device-stage parity can be executed locally; real-device acceptance remains `make parity-gpu` on the target stack. No target-GPU certificate is fabricated in this delivery.

## Completed validation

- JSON configurations: 95/95 load successfully.
- Python compilation: 191 files.
- Full tests: 315 passed, 2 skipped; both skips require a real CUDA/CuPy device.
- Ordinary parity: 20 passed, 2 real-device tests skipped.
- Non-Conda editable verification: 117 modules and 32 console entries, with external empty-`PYTHONPATH` smoke.
- Isolated wheel and sdist release validation passed.
- `make conda-sync` and `make conda-check` were executed and stopped at the real `CONDA_PREFIX` guard; `conda-check` completed its full test phase first.
- `make parity-gpu` was executed and failed at the required-device contract because the delivery host has no usable CUDA/CuPy device.

