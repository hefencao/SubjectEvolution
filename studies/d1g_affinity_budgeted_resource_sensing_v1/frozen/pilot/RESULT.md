# D1-G pilot result

The supplied three-seed panel satisfies the registered shared-checkpoint,
paired-randomness, genotype, resource-field, cost-preservation, radius-one, and
fixed extra-radius budget contracts.

Paired differences for the affinity-budgeted branch minus the cost-preserving
radius-one branch were:

| seed | alive | births | deaths | mean energy |
|---:|---:|---:|---:|---:|
| 86001 | -3 | -4 | -1 | -0.089208 |
| 86002 | -40 | -25 | +15 | +0.090915 |
| 86003 | -15 | -11 | +4 | +0.007554 |

The median living-count difference is -15 and the median mean-energy difference
is +0.007554. Multi-channel Hamilton allocation closes exactly and reaches the
world-facing gradient path, but static inherited affinity does not express
which resource channel is currently needed. The D1-G source protocol also has
no conservative per-channel internal stores, so it cannot expose current
resource demand.

The result supports a carrier-capability composition, not a reward, cost,
threshold, or environment-amplitude change. D1-H combines the existing
conservative four-channel store with the same inherited reach capacity and
costs, and gates its fixed channel budget by current open store room.
