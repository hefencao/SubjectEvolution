# D3-L GPU memory failure analysis

The supplied D3-L run did not fail because the persistent biological or knowledge state itself reached tens of gigabytes.

For seed 69002, the recorded population grew from 14,342 entities at tick 3700 to 22,369 at tick 4500. Active encoded knowledge grew from 3,458,480 bytes to 5,394,048 bytes, and selected latent copies per policy step grew from 11,140 to 18,817. Those changes are substantial computationally but are orders of magnitude smaller than the reported increase from about 2 GiB to about 32 GiB of device residency.

The GPU path creates transient observation, policy and latent-router arrays whose first dimension follows the active population or selected-copy count. CuPy's default allocator retains freed blocks. During a long monotonic population rebound, successive larger shapes can leave a staircase of obsolete smaller blocks in the allocator cache. Device monitors count those cached blocks as process memory even though they are no longer live simulation state.

The old artifacts do not contain allocator-pool telemetry, so this is a strong structural inference rather than a measured decomposition. v0.70 therefore records live bytes, end-of-step cache and post-trim cache separately, and bounds only stale unused cache at the next-step start after the preceding step frame has exited. Live arrays are never evicted, the simulation is not moved to CPU, and model state is unchanged.

Seed 69001 ended at tick 200, while seeds 69002 and 69003 reached tick 4500. These are incomplete fixed-horizon runs and remain failure evidence rather than completed regime-resolution evidence.
