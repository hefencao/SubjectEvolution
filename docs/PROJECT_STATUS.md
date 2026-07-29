# SE project status

Version: **0.63.0**

## Current causal and measurement chain

```text
role-free four-channel external resource and abiotic fields
→ persistent moving channel-specific abiotic renewal targets
→ explicit physical flux and numerical-settlement ledgers
→ inherited affinity, capacities and conservative delayed stores
→ costed spatial processing support with orientation-matched neutral controls
→ preregistered acute panels and nested seed-level effect inference
→ evidence gate before any sensory, migration or ecological mechanism
```

## Supplied D3-I replication result

The supplied artifacts contain eight independent seeds at each of the 1.5× and 2× scales, four preregistered checkpoints per seed and 32 matched four-arm panels per scale. Every panel is acute eligible, but the directional replication gate remains false:

- 1.5× original mean gain: `-2.898296122704174e-06`;
- 1.5× reversed mean gain: `-5.477934432784455e-06`;
- 2× original mean gain: `9.253429667044727e-07`;
- 2× reversed mean gain: `6.064305225430936e-07`;
- both-orientation-positive seed fractions: `0.0` and `0.125`.

This still does not justify a processing-support sensor, movement reward, migration controller or ecological interpretation.

## Supplied backend diagnosis

All 256 supplied branch runs requested `gpu`, but all 256 report:

```text
execution_backend = gpu-strict-reference
gpu_semantics_mode = strict-reference
gpu_acceleration_enabled = false
cpu_reference_world_authoritative = true
```

They are valid CPU-authoritative runs, not accelerated GPU runs. The previous default therefore prevented practical large-scale GPU long runs.

## v0.63 decision

Change the execution default, not the scientific mechanism:

- all high-level run and experiment entry points default to `auto`;
- configuration defaults use `hybrid-accelerated` GPU semantics;
- a usable CUDA/CuPy device runs the real hybrid GPU path;
- a host without a usable GPU continues on CPU and records `cpu-fallback-no-gpu` and its reason;
- `strict-reference` remains an explicit historical diagnostic, not the production default;
- CPU/GPU semantic validation belongs to `tests/test_parity.py`, not to a runtime fallback that disables acceleration.

Parity v2 compares every checkpoint-authoritative semantic leaf, dedicated persistent device mirrors and a representative matrix of current semantic families. Real-GPU parity tests skip only when no CUDA device is available.

## Next gate

Run `test_parity.py` on the target GPU environment before treating accelerated output as cross-backend validated. Then rerun the fixed D3-I panels with the default `auto` backend and verify `run_manifest.json` reports `gpu-hybrid-accelerated` and `gpu_acceleration_enabled=true`.

Do not add a response mechanism while the supplied eight-seed directional replication gate remains false. Evolutionary claims remain blocked until the separate generation-turnover gate is met.

## Still incomplete

- successful real-GPU parity across all registered semantic families on the target CUDA stack;
- performance and memory measurements for 1.5× and 2× accelerated panels;
- positive, stable processing-response replication under both orientations;
- adequate generation turnover for evolutionary inference;
- justified sensing or control for processing opportunity;
- migration, specialization, coexistence or trophic evidence;
- externalization and evolved reuse of non-store body matter;
- entity-to-entity material transfer and consumption;
- dynamic module topology or copy-number evolution.
