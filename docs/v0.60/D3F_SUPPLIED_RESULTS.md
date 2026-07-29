# D3-F inventory-conditioned spatial-processing response audit

Schema: `d3-spatial-processing-response-results-v1`

| Seed | Branch | Resource moves | Mean support gain | Positive gain fraction | Mean gradient cosine |
|---:|---|---:|---:|---:|---:|
| 59001 | original-support | 22197 | -0.0003426038286041968 | 0.40509978825967474 | -0.15294387801965 |
| 59001 | reversed-support | 21416 | -7.5383976556830865e-06 | 0.4851512887560702 | -0.01492807463433921 |
| 59001 | neutral-support | 23561 | -0.00030879930140583324 | 0.41059377785323203 | -0.14330175411911733 |
| 59002 | original-support | 19040 | -0.00029272161339919853 | 0.4244747899159664 | -0.11958853952629596 |
| 59002 | reversed-support | 20411 | -3.176948189563321e-05 | 0.48767821272843076 | -0.009751180473128595 |
| 59002 | neutral-support | 19852 | -0.0003575605887271721 | 0.40565182349385454 | -0.14637056556243136 |
| 59003 | original-support | 23274 | -0.00036995453846555494 | 0.41007132422445647 | -0.15408956534491977 |
| 59003 | reversed-support | 22471 | 6.027527711236634e-06 | 0.4937919985759423 | -0.0025693842513764367 |
| 59003 | neutral-support | 23839 | -0.0003508923130682491 | 0.4068543143588238 | -0.14795581545588862 |

## Audit completeness

- shared tick0 checkpoint in every triplet: `True`
- response trajectory complete in every branch: `True`
- resource movement observed in every branch: `True`
- active support exposure nonuniform in every active branch: `True`
- neutral support exactly one in every neutral branch: `True`
- external resource ledger valid in every branch: `True`
- external recycling ledger valid in every branch: `True`

Recommendation: `response-audit-complete-inspect-repeated-orientation-alignment`

Support-orientation and neutralization branch differences are attributable to their registered interventions under the shared checkpoint contract. Movement alignment remains an observed mediator and is not itself a migration or specialization proof.

D3-F measures inventory-conditioned movement relative to original, reversed, and neutral processing-support surfaces without adding a support sensor, reward, or controller. Repeated orientation-aligned response is a prerequisite for later migration tests, not evidence of ecotypes, coexistence, trophic transfer, or named roles.
