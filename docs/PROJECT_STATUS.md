# SE project status

Version: **0.35.0**

## Current focus

The project is in the environment-and-differentiation-first phase:

1. D0 orthogonal environmental constraints;
2. D1 elastic capacities;
3. D2–D3 functional modules and structural mutation;
4. D4 ecological niches and coexistence;
5. D5 social organization and higher-level candidate subjects.

## v0.35 structure

- import root changed from `subject_evolution` to `se`;
- generic `domains/` and `interfaces/` layers removed;
- environment domain moved to `se.env`;
- GUI moved to `se.gui`;
- command implementations moved to `se.cmd`;
- `config.py` became `cfg.py`;
- runtime engine became `se.runtime.sim`;
- historical checkpoint bridge removed;
- scientific config field names and schemas remain fully spelled;
- active docs contain only current guidance; detailed old release reports remain in old release bundles.

## Current scientific boundary

- D0 supplies multiple exogenous environmental axes but has not yet demonstrated heritable phenotype or niche differentiation.
- Existing four resource channels and body-effect ports remain a fixed model substrate.
- Subject succession remains a group-label-dependent diagnostic, not proof of an autonomous higher-level subject.
- D1/D2 are not implemented and current knowledge memory/router components must not be relabeled as general organ differentiation.

## Next run

```text
configs/mvp_short_d0_orthogonal_env_longrun.json
```

Recommended first evaluation: 3 seeds × 1500 ticks, followed by resource-dimension retention, limiting-factor use, affinity trade-offs, phenotype clustering and long-term coexistence analysis.
