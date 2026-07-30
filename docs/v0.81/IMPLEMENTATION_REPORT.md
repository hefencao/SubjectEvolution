# v0.81 implementation report

## Result accepted

The supplied D3-T replication retains the preregistered screen result on eight disjoint seeds. All operational manipulation checks pass, all seed effects retain the suppressive-support direction, and the equal-seed median relative effect is approximately +2.546%, above the unchanged 2% threshold. The next authorized stage is exact-protocol confirmation.

## Root cause addressed

The project previously used `analyses/` for source simulations, checkpoints, intervention branches, assessments, and mutable decision state. Historical plans also depended on candidate labels and machine-specific paths. This made cross-version continuation fragile and caused a valid generic source cohort to appear incompatible with its later paired candidate.

v0.81 replaces one-off path or candidate rewrites with a study evidence chain. The owning study contains design, candidate/config protocols, ordered commands, and frozen compact evidence. Runtime is outside the study under `runs/`; derived reports are under `analyses/`; mutable overlays are under `state/`. D3-O through D3-S are also represented as decision-only legacy bundles, with every unavailable artifact class declared instead of reconstructed.

## Cross-version contract

Each frozen stage records the candidate signature, exact source-plan hash, source protocol fingerprint, evidence hashes, decision, seed set, and canonical checkpoint identities. Legacy generic source candidate IDs are accepted only when the paired evidence binds the exact source-plan content. Legacy stage migration validates compact frozen evidence and every checkpoint anchor before writing, then separates source runtime, intervention runtime, and derived analysis into their canonical roots. A checkpoint-only content-addressed migration remains available when the rest of the old runtime tree is not retained.

## Command discipline

The root and study README files contain navigation and interpretation only. Exact commands are isolated in numerically ordered shell files under the study's `commands/` directory. This keeps a single authoritative execution chain per result.

## Verification immutability

`se-study-verify` computes the expected chain and run summary in memory and never rewrites frozen evidence. Rebuilding remains an explicit freeze/rebuild action. Test and release freshness fingerprints cover source inputs but exclude ignored generated metadata such as `*.egg-info`, bytecode, and build directories, preventing distribution builds from invalidating an otherwise fresh test report.
