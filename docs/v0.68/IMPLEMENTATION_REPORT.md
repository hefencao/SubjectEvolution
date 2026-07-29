# v0.68 implementation report

v0.68 responds to the D3-J observation that all three 8,000-entity runs contract to roughly 900 entities near tick 800 and then rebound modestly. The final lineage distribution remains broad, so the correct next question is not simply whether a bottleneck occurred, but whether a descendant-dominated, reproductively broad and demographically stable source emerges afterward.

## Runtime additions

Each long-run evolution window now records:

- generation-zero survivors and living descendants;
- living-descendant fraction;
- unique successful parents;
- inverse-Simpson effective successful parents;
- largest parent contribution fraction.

The parent metrics use stable entity IDs. Repeated births by one parent increase its contribution weight rather than increasing the independent-contributor count.

## Analysis additions

`demographic-selection-validity-audit-v2` adds `post-bottleneck-demographic-regime-v1`. A source-ready pilot must satisfy recent-window population stability, absolute population support, lineage breadth, generation turnover, descendant replacement and parent-contributor breadth.

`multi-seed-long-run-analysis-v16` now embeds the demographic audit rather than dropping the v0.67 fields. `se-multi` writes `multi-seed-run-plan-v2` before the first seed and automatically emits selection-validity artifacts afterward.

## Interpretation boundary

A source-ready result does not validate the pilot itself. It only permits a fixed burn-in rule to be preregistered for new independent seeds. No demographic threshold feeds back into the world, and no failed seed is replaced.

## Validation

- 97 JSON configurations load successfully.
- 194 Python files across `src/`, `scripts/`, and `tests/` compile successfully.
- Full deterministic test shards: 329 passed, 2 real-CUDA-only tests skipped, 66 test files.
- Ordinary parity: 20 passed, 2 real-CUDA-only tests skipped.
- Editable installation: 118 modules and 33 console entries, including an external empty-`PYTHONPATH` smoke run.
- Isolated wheel and sdist release audit passed.
- The delivery host has neither an active Conda environment nor a usable CUDA/CuPy device; their strict guards were not bypassed.
