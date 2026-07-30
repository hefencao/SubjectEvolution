# v0.70 implementation report

v0.70 addresses a GPU allocation-lifetime failure observed during the D3-L population rebound.

## Implementation

- Added `GpuMemoryPoolController` as a backend-execution component.
- Added `bounded-cache-v1` and retained an explicit `unbounded-default-v1` diagnostic policy.
- Added configurable cache limit and trim cadence to `RunConfig`.
- Integrated allocator trimming at the next-step start boundary, after the preceding step frame and its temporary references have exited.
- Published live, end-of-step pool/cache, post-trim pool/cache, peak, trim, released-byte and pinned-pool telemetry.
- Extended GPU execution auditing and added a directory-oriented memory-stability audit.
- Added D3-M without changing world or evolutionary parameters.

## Semantic boundary

The controller can release only blocks the allocator already considers unused. Referenced arrays remain allocated. No random stream, world state, checkpoint field, policy input, action, birth, death, knowledge copy or relation is changed.

## Supplied-run interpretation

The supplied artifacts predate allocator telemetry. Their entity and knowledge growth is much smaller than the reported device-residency growth, which strongly implicates retained transient blocks. D3-M is required to measure the decomposition directly and complete the fixed horizon.
