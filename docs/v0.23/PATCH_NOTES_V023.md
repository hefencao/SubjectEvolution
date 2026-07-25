# Subject Evolution v0.23.0

## Direction change

Synthetic moving hazards are no longer an in-core scientific mechanism. Optional environment processes are isolated behind a scalar-field plugin boundary and are disabled in the flagship scientific long-run configuration.

## Added

- `environment_process.py`: registry, protocol, entry-point discovery, validation, metadata and v0.22 resolution adapter;
- `plugins/moving_gaussian_hazard.py`: unchanged numeric moving-Gaussian formula as a synthetic abiotic compatibility plugin;
- generic `environment_process_schema` and `environment_process_parameters` configuration fields;
- environment-process provenance in manifests, metrics and long-run analysis v7;
- scientific-validity rejection of synthetic observation/entertainment extensions;
- generic plugin example configuration and six extension-boundary tests.

## Preserved

- default scientific world trajectory;
- v0.22 moving-hazard numeric trajectory through the adapter;
- old checkpoint configuration hashes;
- CPU/NumPy-device parity;
- all K1–K4, latent L1/L2, memory, Top-k, transfer, mortality trace, adaptive groups and local-culture behavior.

## Validation

- `117 passed, 1 skipped`;
- skipped test requires a real CUDA/CuPy device;
- 10-tick v0.22/v0.23 compatibility: 308 common non-timing metric fields exact in both disabled and moving-hazard conditions;
- seven knowledge/event logs byte-identical in both conditions;
- scientific baseline smoke run resolves `environment_process=disabled` and remains structurally valid;
- synthetic plugin smoke run is explicitly excluded from the scientific ecology baseline.
