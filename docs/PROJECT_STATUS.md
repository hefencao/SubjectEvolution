# SE project status

Version: **0.66.0**

## v0.66 reporting and plan boundary

The supplied scale-4 runs exposed a mixed-age summary: current tick/entity
counters were combined with a residue field last synchronized by the preceding
full checkpoint. v0.66 treats reporting as its own authoritative boundary.
Every metrics row materializes current device-owned fields and records the
materialized tick; checkpoint cadence can no longer change summary freshness.

A fixed `run_plan.json` is written before stepping. It records target tick,
backend, metrics cadence and checkpoint schedule without using outcomes to
change the run. This fills the missing plan artifact while preserving the
project rule against outcome-conditioned checkpoint or seed selection.

## Current causal and measurement chain

```text
role-free four-channel abiotic resources
→ conservative storage, recycling and persistent renewal
→ costed spatial processing with orientation-matched neutral controls
→ preregistered acute panels and seed-level inference
→ GPU-first execution + target-device parity certificate
→ large-population source runs before any new response mechanism
```

## Supplied GPU evidence retained

The supplied D3-I artifact contains 128/128 real `gpu-hybrid-accelerated` branches with no fallback or strict-reference execution. It proves execution provenance, not speedup or scientific effect. The response replication gate remains closed and no checkpoint is evolutionarily sufficient.

Low-population windows near 100–300 alive are not used as a GPU throughput gate. Their launch, transfer and CPU-settlement overhead is expected to dominate. v0.65 therefore moves directly to density-preserving source populations of 8,000 and 32,000 entities.

## v0.65 execution boundary

Ordinary hybrid ticks keep these inputs device resident:

- inherited resource-affinity quantization;
- inherited danger-evidence quantization;
- policy resource utility;
- oxygen/terrain/wear fields and oxygen gradients;
- information detection summaries when full diagnostics are not due.
- exact uint64 latent-root hash components during batches of new independent experience contents.

The CPU remains authoritative for intent settlement, lifecycle, relation/subject graph changes, knowledge outcome commit order, final latent floating accumulation/quantization and output writing. The runtime reports actual transfer bytes separately from semantic host traffic avoided, and reports `gpu_device_latent_root_rows` for the newly migrated integer-hash batch.

Long `run()` calls defer full field synchronization. Local physiology and terrain settlement now query current device fields by active cell; low-frequency metrics and checkpoints explicitly materialize current device fields. This prevents stale CPU mirrors from affecting long GPU trajectories.

The large-population presets keep authoritative knowledge mechanisms, energy
costs, aggregate counters, transfer events and full checkpoints, but disable
five dense per-entity/per-candidate CSV streams. On the target RTX 4070, a
100-tick scale-4 probe otherwise produced about 674 MiB of output (about
553 MiB from policy contributions alone). Removing only those observational
streams reduced the measured mean tick time from 0.737 s to 0.421 s; this is a
throughput result for one host/device pair, not a scientific effect or a general
GPU speedup claim.

Both large-population base presets now produce observation and full-world
checkpoints every 100 ticks. A real scale-4 run produced a 19 MiB `.npz` and
36 MiB `.sechk` at tick 100; the bundle checksum passed and the run resumed on
the GPU from tick 100 to tick 101. This cadence does not make a checkpoint
evolutionarily sufficient. It only improves recovery and supplies more
predeclared base states for later shared-checkpoint experiments.

The first post-I/O migration targets deterministic latent-root hashing rather
than floating world settlement. New independent roots are still accepted in
the same CPU canonical order, while SplitMix64-derived root/action/context and
outcome-projection signs are computed in device batches. Final accumulation
and int16 quantization use the historical CPU scalar order. On the RTX 4070,
22/22 real-device parity tests passed. A matched 20-tick cProfile decreased
from 22.9 s to 14.0 s; a non-profiler 100-tick window changed more modestly
from 0.4211 to 0.4098 s/tick because root creation is concentrated early and
other CPU-authoritative stages remain.

## Validation boundary

- `make test` validates the CPU/no-device build and CPU-emulated parity stages.
- `make parity-gpu` is mandatory on each target CUDA/CuPy stack and produces the archival parity certificate only when every registered semantic family passes.
- GPU execution provenance and parity are separate from performance claims.
- Performance work is evaluated on large source populations, not late low-population response windows.

## Next gates

1. Archive a `make parity-gpu` certificate for the exact target stack; the direct required-device parity suite currently passes 22/22.
2. Continue the 8,000-entity base run with 100-tick checkpoints and retain storage/transfer telemetry.
3. Measure scale-8 checkpoint size and write latency before committing to its full 1,500-tick storage budget.
4. Profile and migrate the remaining latent finalization/router, functional-output and CPU settlement boundaries only with semantic-family parity.
5. Keep the processing-response mechanism gate closed until replicated response and generation-turnover requirements are met.

## Still incomplete

- archived successful parity certificate for the exact target CUDA/CuPy stack;
- measured scale-8 GPU scaling, checkpoint storage and memory headroom;
- device-resident action settlement, lifecycle and graph updates;
- device-resident final knowledge learning/quantization and sparse output pipeline;
- positive replicated processing-response evidence;
- adequate generation turnover for evolutionary inference;
- migration, specialization, coexistence or trophic evidence.
