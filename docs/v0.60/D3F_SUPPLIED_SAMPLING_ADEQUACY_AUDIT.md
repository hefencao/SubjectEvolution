# D3-F response sampling-adequacy audit

Schema: `d3-processing-response-adequacy-audit-v1`

| Seed | Branch | First < alive floor | Initial entity-tick share | Initial move share | Post-burn-in population support |
|---:|---|---:|---:|---:|---:|
| 59001 | original-support | 420 | 0.46578378437102785 | 0.5694463215749876 | False |
| 59001 | reversed-support | 360 | 0.4779562533173171 | 0.5992715726559582 | False |
| 59001 | neutral-support | 420 | 0.4366337188852469 | 0.5327447901192649 | False |
| 59002 | original-support | 360 | 0.5356520838324129 | 0.6134453781512605 | False |
| 59002 | reversed-support | 360 | 0.5323185840707965 | 0.5757189750624663 | False |
| 59002 | neutral-support | 390 | 0.5374952782775156 | 0.601501108200685 | False |
| 59003 | original-support | 360 | 0.5033626487325401 | 0.5436538626793848 | False |
| 59003 | reversed-support | 330 | 0.5099795664028645 | 0.5517333452004807 | False |
| 59003 | neutral-support | 360 | 0.48004342850435755 | 0.528252023994295 | False |

## Summary

- mechanism audit complete: `True`
- population supported long run inference: `False`
- movement events are independent replicates: `False`
- independent unit: `seed/checkpoint panel`
- initial block entity tick fraction min: `0.4366337188852469`
- initial block entity tick fraction max: `0.5374952782775156`
- initial block resource move fraction min: `0.528252023994295`
- initial block resource move fraction max: `0.6134453781512605`
- evolutionary inference supported by generation data: `False`

Recommendation: `retain-mechanism-audit-but-replace-single-long-run-with-preregistered-acute-checkpoint-panel`

This audit separates mechanism integrity from sampling support. Movement events are temporally and genealogically clustered and are not independent replicates. The supplied result does not contain enough generation history to authorize evolutionary inference.
