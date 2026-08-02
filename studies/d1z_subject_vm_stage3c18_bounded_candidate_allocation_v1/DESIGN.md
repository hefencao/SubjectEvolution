# Design

Stage 3C-18 keeps the Stage-3C-17 latest ordering, candidate validity, normalized-dot score, delay bounds, similarity threshold, `edge_forward_gate` target, edge eligibility carrier, horizon, exposure, bounded delta, rollback and score-free evaluation fixed. The baseline selects one candidate. The alternative selects at most two candidates under the same ordering and uses the equal-weight arithmetic mean of their objective-fact vectors as the single historical comparison vector.

This is a bounded addressing-cardinality diagnostic. Equal weighting does not assign value, causal quality, trust or reward to either candidate. The two-candidate arm does not emit two modulation proposals, does not double the event delta budget and does not authorize permanent retention.
