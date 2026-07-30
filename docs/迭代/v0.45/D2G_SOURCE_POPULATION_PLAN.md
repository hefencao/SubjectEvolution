# D2-G source-population reconstitution plan

Schema: `d2-source-population-plan-v1`
Candidate modules retained for later retest: `3`
Source endpoint reproduced: `False`
Transient causal chain supported: `True`
Burn-in: `600` ticks
Observation offsets: `0, 120, 300, 600`

## Design boundary

- Genotypes only are transferred from unique living donors without replacement.
- Physiology, age, knowledge, social state and spatial position are reset.
- Equal-lineage and natural-abundance arms use the same total founder count.
- No lineage-aware reward, survival protection, spatial reservation or reproduction rule is added.
- Module copy number and routing vocabulary remain unchanged.

| Panel | Phase | Seed | Donor lineages | Founders | Equal per lineage |
|---|---|---:|---:|---:|---:|
| `peak_seed_45001` | peak | 45001 | 6 | 288 | 48 |
| `peak_seed_45002` | peak | 45002 | 6 | 288 | 48 |
| `peak_seed_45003` | peak | 45003 | 6 | 288 | 48 |
| `trough_seed_45001` | trough | 45001 | 6 | 288 | 48 |
| `trough_seed_45002` | trough | 45002 | 6 | 288 | 48 |
| `trough_seed_45003` | trough | 45003 | 6 | 288 | 48 |

The natural-abundance arm is a paired composition control. The equal-lineage arm is only a candidate source population after unprotected burn-in; tick-zero equalization itself is not evidence of stable diversity.
