# v0.45 implementation report

v0.45 implements D2-G source-population reconstitution and qualification.

## Added

- `d2-source-population-plan-v1`;
- `d2-source-population-results-v1`;
- `d2-source-population-assessment-v1`;
- `se-d2-source-population`;
- `se-d2-source-population-assess`;
- genotype-only founder installation at tick zero inside the experiment runner;
- paired natural-abundance and equal-lineage fresh-world arms;
- multi-offset lineage-guard and module-expression observations;
- source-population qualification across fresh seeds and donor phases.

## Boundaries

The implementation does not modify ordinary simulation initialization, world rules, policy observations, reproduction, lineage inheritance, module copy number or routing. The founder installer is called only by the explicit D2-G experiment. It transfers unique donor genotypes without replacement and rebuilds all subject, knowledge and evolution-baseline state for the fresh population.

## Input retention

The project package retains the compact supplied D2-F Markdown assessment and the generated D2-G plan. The multi-megabyte row-level assessment JSON is not duplicated into version documentation; its SHA-256 is recorded in the generated plan and the user-provided analysis bundle remains the authoritative raw input.
