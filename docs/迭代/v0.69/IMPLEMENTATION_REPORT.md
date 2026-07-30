# v0.69 implementation report

v0.69 corrects the demographic regime boundary and keeps release documentation portable.

## Regime classification

`demographic-selection-validity-audit-v3` adds normalized recent population slope and total cross-window population change. The earlier coefficient-of-variation and per-window growth checks remain, but no longer allow monotonic growth to be called settled.

The supplied D3-K aggregate is reclassified as three active post-bottleneck rebounds. The result supports continued fixed-horizon observation, not a burn-in rule or a selection claim.

## Lineage and current variation

Evolution progress now records Shannon-effective founder lineages, inverse-Simpson effective founder lineages, lineage-count retention, and top-1/top-5/top-10 family shares. The selection audit separately carries current canonical diversity, policy diversity and strategy effective dimensions when available. Founder-family concentration is not used as a synonym for all heritable variation.

## Scientific boundary

No world mechanism, mortality pressure, birth pressure, population support, diversity protection, reward, sensor or ecological role was added or modified.
