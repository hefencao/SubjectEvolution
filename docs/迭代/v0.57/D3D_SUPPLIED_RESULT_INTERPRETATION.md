# Supplied D3-D result interpretation

## Source material

The supplied panel uses seeds `56001`, `56002`, and `56003`, a 1500-tick horizon, `orthogonal-four-resource-renewal-v2`, and `moving-target-source-sink-v2`. It explicitly disables named resource roles, diversity protection, ecological role labels, and entity/lineage/group feedback into renewal.

## Supported observations

| Seed | Alive | Initial effective dimensions | Final effective dimensions | Final mean absolute correlation | v1 ledger |
|---:|---:|---:|---:|---:|---:|
| 56001 | 84 | 3.992824 | 2.857844 | 0.074211 | false |
| 56002 | 112 | 3.992824 | 2.936019 | 0.108817 | false |
| 56003 | 104 | 3.992824 | 2.978755 | 0.192976 | false |

Across all seeds:

- both renewal source and renewal sink occur;
- external recycling remains conservative;
- multiple resource dimensions persist;
- the old open external-resource ledger fails its tolerance.

These observations retain the persistent-opportunity substrate. They do not establish collection-processing specialization, migration, coexistence, trophic transfer, or named resource roles.

## Diagnosis

The v1 ledger compares high-precision cumulative flux totals to a global inventory stored and updated in `float32`. It omits:

1. signed inventory settlement introduced when renewal, release, diffusion and clipping are committed to the field;
2. signed inventory settlement introduced when admitted harvest is subtracted through segmented float32 accumulation.

The three-seed residual is small relative to cumulative throughput and has a consistent numerical pattern. A 300-tick instrumented replay shows that the old residual is exactly explained by these two omitted terms to floating-point precision.

This diagnosis does not modify the supplied result or silently relabel it valid. The v1 files remain failed under their own schema. v0.57 supplies a v2 measurement contract and requires a new long-run report.

## Decision

- retain D3-D;
- correct the measurement boundary;
- do not add D3-E in this release;
- rerun the shared config and seeds under results v2;
- require corrected ledger closure and persistent dimensions before reconsidering collection-processing coupling.
