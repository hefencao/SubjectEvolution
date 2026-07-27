# D2-G source-population reconstitution

## Input decision

The supplied D2-F result contains a transient routed-output chain for module 3: target-lineage mean energy becomes positive at 120 ticks, total energy at 180 ticks, shared energy at 180/240 ticks, harvest at 240 ticks, and demographic outcomes change later. The original persistent 300-tick mean-energy endpoint is not reproduced at the final D2-F offset, and several demographic outcomes reverse direction over time.

This is evidence that the fixed module can alter downstream flow, energy and demography in some contexts. It is not evidence for a stable ecological advantage, and it does not release the copy-number gate. The source checkpoints remain lineage-dominated.

## Question

Can a fresh population assembled from inherited genotypes across independent source runs retain at least four expressed lineages after ordinary, unprotected burn-in?

## Founder design

D2-G creates two paired initial-condition arms from the same preregistered donor checkpoints:

1. `natural-abundance-control`: the selected donor lineages contribute in proportion to their pre-intervention abundance;
2. `equal-lineage-reconstitution`: the same selected lineages contribute the same number of unique donor individuals.

The total founder count is identical across arms. Donors are sampled without replacement. Only genotype is transferred; energy, integrity, material, information, fertility, age, generation, knowledge, social state and spatial position are reset by constructing a fresh world.

For each peak/trough phase, the plan selects the two most abundant pre-intervention lineages from each of the three original seeds. It does not inspect lineage-specific D2-F responses. The supplied plan therefore contains six lineages per phase, 48 founders per lineage in the equal arm and 288 founders per panel.

## No diversity protection

Equalization occurs once at tick zero as an explicit initial-condition intervention. After initialization:

- world, policy and reproduction rules do not read the panel lineage identity;
- no lineage receives survival, fertility, resource, spatial or sampling protection;
- no lineage is restored after decline or extinction;
- no ecological role is assigned;
- module copy number and routing vocabulary remain unchanged.

Tick-zero equality is not evidence. Qualification is based on the population after 600 ticks of ordinary dynamics.

## Qualification

A phase is qualified only when at least two independent fresh-world seeds satisfy all final burn-in conditions in the equal-lineage arm:

- effective lineages at least 4.0;
- dominant lineage fraction at most 0.5;
- at least four panel lineages retain eight or more living members;
- module 3 remains expressed in at least four eligible lineages.

Both peak and trough donor phases must qualify. The natural-abundance arm is reported as a paired composition control but is not required to fail.

Even a qualified source population does not authorize copy-number change. It only provides frozen, multi-lineage checkpoints on which the baseline module-3 causal effect must be re-estimated before a later copy-number experiment can be preregistered.
