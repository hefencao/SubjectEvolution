# v0.47 → v0.48 compatibility

The archived v1/default configuration `configs/mvp_small.json` was run for 20 CPU ticks from both versions with an exact tick-20 checkpoint.

After normalizing only newly introduced default-disabled fields:

- authoritative checkpoint semantic leaves compared: `139689`;
- checkpoint differences: `0`;
- public checkpoint arrays: all identical;
- common non-timing summary differences: `0`;
- common non-timing metrics differences: `0`.

The v2 compositional path is opt-in. Existing v1 configs do not receive coupling genes and retain the archived evaluation trajectory.
