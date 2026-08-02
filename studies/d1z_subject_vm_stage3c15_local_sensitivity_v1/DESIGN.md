# Stage 3C-15 design boundary

## Diagnostic question

Stage 3C-14 showed that `node_bias` and `node_output_gate` are both reachable but have different short-term visibility. Stage 3C-15 does not open another family in the live-write chain. It first asks which of all six generic parameter roles are locally visible at the current fixed-bootstrap operating point, which are algebraically degenerate, and which are sensitive but unavailable to the current eligibility selector.

## Probe contract

The diagnostic replays bounded `±0.05` external finite-difference probes from the same quiescent source checkpoint. Each branch changes one parameter family at one fixed bootstrap slot and runs one semantic tick. Probe writes are not saved to the source checkpoint and do not authorize parameter retention.

Two contexts are required:

1. the first activation after bootstrap;
2. one unperturbed activation later, when the one-tick delayed edge has prior node state.

The second context prevents delayed-edge zero response at the first activation from being misclassified as permanent inactivity. `edge_bandwidth` uses an inward one-sided probe because its bootstrap value is already at the configured upper bound.

## Target slots

- `node_bias`, `node_input_gate`, `node_output_gate`: node 0;
- `node_trace_gate`: token-emitting node 7;
- `edge_forward_gate`, `edge_bandwidth`: edge 0.

These slots are diagnostic operating points, not a new target-binding policy.

## Interpretation boundary

Local derivative magnitude is not benefit, value, credit quality or family preference. A zero derivative may be caused by the operating point, delayed state, inactive clamp or missing route. A nonzero derivative does not authorize eligibility, live write, retention, learning or subjecthood claims.
