# v0.74 implementation report

v0.74 records the completed D3-P capacity-use screen, distinguishes manipulation-confirmed negative candidates from legacy promotion failures without a direct manipulation contract, and opens one broader bounded candidate.

## D3-P decision

The intervention engages in all eight seeds: baseline capacity dimensions remain positive and intervention dimensions are zero. The realized working-memory-use response is four positive and four negative seed effects, with an equal-seed median relative effect below the preregistered threshold. The candidate is terminal and cannot enter replication.

## Candidate ledger v2

The ledger now records target-engagement evidence separately from effect-promotion evidence. Legacy v1 ledgers are accepted and upgraded in memory. A manipulation-confirmed negative candidate means the declared target changed as intended but the seed-level effect gate failed; it remains specific to the preregistered metric, horizon and threshold.

## D3-Q bounded gate

D3-Q disables the full knowledge-policy residual and tests total harvested resource. It requires direct proof that the residual changed baseline actions and changed no intervention actions. This is a broader causal gate than another capacity subcomponent audit and reuses the existing fixed checkpoint set.

## Repository ignore policy

The project root `.gitignore` is the user-supplied file without normalization or deduplication.
