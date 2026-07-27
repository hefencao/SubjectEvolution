# D4-A resource-geography × inherited-affinity reversal

## Question

Do inherited four-resource affinity differences causally change lineage persistence when resource geography is reversed?

The experiment does not ask whether the existing module names correspond to ecological roles. It tests a lower-level charter requirement: different inherited phenotypes should have condition-dependent consequences under a changed multidimensional environment.

## Source checkpoints

The plan preserves both D2-G equal-lineage peak checkpoints that passed the preregistered source-population guards:

- `peak_seed_45001`, tick 600;
- `peak_seed_45003`, tick 600.

Every lineage retained by the D2-H source plan remains in D4-A. No lineage is selected by its D2-H response.

## Four branches

| Branch | Resource geography | Expressed affinity |
|---|---|---|
| baseline | original | inherited |
| resource-reversed | rotated 180° | inherited |
| affinity-neutral | original | uniform |
| joint-neutral | rotated 180° | uniform |

The primary difference in differences is:

```text
(baseline - resource-reversed)
- (affinity-neutral - joint-neutral)
```

This interaction is zero when resource reversal has the same effect with inherited and uniform affinity. A material non-zero interaction means the consequence of resource geography depends on inherited affinity expression.

## Resource-only reversal

`reverse-resource-geography`:

- rotates all four current resource fields by 180 degrees;
- persistently rotates future seasonal regeneration templates;
- retains channel identity, capacity, regeneration magnitude, diffusion and effect matrix;
- does not rotate hazard or mortality trace;
- does not move entities or modify entity state;
- does not consume random draws.

The intervention is stored in checkpoint state and mirrored by the device environment.

## Source exposure diagnostic

Before branch execution, each planned lineage receives a read-only diagnostic:

1. local resource fractions under the original field;
2. local fractions at the same positions after a 180-degree field rotation;
3. utility under inherited affinity;
4. utility under uniform affinity;
5. affinity-specific exposure advantage.

Exposure alignment can connect a causal endpoint interaction to a concrete pre-intervention phenotype–environment relation. It is not counted as a separate seed or intervention.

## Screen gate

The 120-tick screen can continue only when a practical affinity × environment interaction has the same direction in:

- at least two independent panel seeds;
- at least two non-dominant checkpoint-lineage identities.

The assessment reports exposure alignment and dominant affinity-channel coverage separately.

A passing screen generates a 300-tick plan that preserves all original checkpoints and all preregistered lineages. It does not select only responsive lineages.

## Interpretation boundary

D4-A can establish causal environment matching. It cannot alone establish stable ecological niches. A niche claim still requires persistent interaction, stable coexistence, phenotype/ecotype removal, and map-scale or template checks.
