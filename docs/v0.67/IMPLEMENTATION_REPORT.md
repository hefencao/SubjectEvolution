# v0.67 implementation report

v0.67 responds to the observation that an 8,000-entity source can collapse to
roughly 1,000 entities before meaningful generation turnover. A long tick count
alone is not treated as evolutionary evidence when the trajectory has already
passed through a severe demographic bottleneck.

This release adds measurement, not population support:

- canonical death-cause signature accounting is recorded per tick, cumulatively,
  in checkpoints and in evolution windows;
- every evolution window reports population fraction relative to initialization,
  cumulative replacement, effective lineages and generation depth;
- `se-selection-validity-audit` separates demographic support from generation
  turnover and classifies collapse-before-turnover trajectories as bottleneck
  dominated;
- failed runs and windows are retained and never replaced by outcome;
- a 1,200-tick scale-4 demographic-audit preset records checkpoints, metrics and
  evolution windows every 100 ticks.

No death pressure, birth probability, carrying capacity, resource supply,
selection coefficient, reward, sensing, diversity protection or lineage
protection is changed.
