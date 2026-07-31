# D1-F affinity-routed resource-sensing reach

## Motivation

D1-E maintained distinct resource wavelengths, but the inherited sensor used
one radius for all four channels. A larger radius therefore discarded local
detail from every channel at once. The acute cost-preserving neutralization was
negative in all three seeds, and the environment still showed substantial
cross-channel correlation.

D1-F changes the carrier capability rather than tuning costs or rewarding a
radius. Morphology gene 7 still determines one inherited reach capacity from
levels 1, 2, 4, and 8. The existing fixed-budget resource-affinity genes route
that extended reach to exactly one strongest-affinity channel; the other three
channels retain radius-one gradients. Deterministic lowest-index tie breaking
is part of the schema.

## Cost and ablation boundary

Maintenance, use, and development costs remain functions of the inherited
reach-capacity gene and are unchanged from D1-E. The existing
`neutralize-resource-sensing-radius` intervention sets every effective channel
radius to one while preserving genotype, affinity, costs, resource fields, and
shared checkpoint state.

## First run

The first three-seed panel is a mechanism calibration only. It checks that
channel routing is expressed and produces non-degenerate paired consequences
under the unchanged D1-E persistent multiscale environment. There is no
post-hoc threshold and no ecological, adaptive, coexistence, or selection
claim.
