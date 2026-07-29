# SE v0.68

SE is a deterministic artificial-life and subject-structure research platform. The current main line retains role-free four-channel resources, conservative storage and recycling, persistent abiotic renewal, costed spatial processing, matched controls, GPU-first execution, and explicit scientific-validity gates.

## Why v0.68

The supplied D3-J runs do not show a simple one-way extinction trajectory. All three seeds contract from the 8,000-entity initialization, reach a trough near tick 800, and then rebound modestly by tick 1200. Final effective-lineage counts remain broad and no lineage approaches monopoly. That makes two interpretations possible:

1. a bottleneck that remains dominated by founder sampling and weak turnover;
2. an initialization-to-carrying-regime relaxation followed by a potentially usable descendant population.

The v0.67 runtime already recorded generation depth, replacement and death causes, but `long_run_analysis-v15` did not expose those fields. v0.68 closes that analysis gap and adds reproductive-contributor breadth so repeated births by the same few parents cannot masquerade as many independent selection samples.

No population is rescued. No death, birth, resource, carrying-capacity, reward, sensing, diversity or lineage-protection parameter is changed.

## Automatic multi-seed provenance and validity audit

`se-multi` now writes `multi_seed_plan.json` before the first seed starts. After all available seeds finish it automatically writes:

```text
long_run_analysis.json / .md
selection_validity_plan.json
selection_validity_audit.json / .md
multi_seed_index.json
```

The independent unit remains the seed. Periodic windows are repeated measurements inside that seed.

Run the extended D3-K source audit:

```bash
se-multi \
  --config configs/mvp_d3k_gpu_scale4_settled_regime_audit.json \
  --seeds 68001,68002,68003 \
  --output analyses/d3k_scale4_settled_regime \
  --backend auto \
  --until-tick 3000
```

The source-readiness audit requires all of the following in recent fixed windows:

- stable absolute population rather than only a fraction of the oversized initialization;
- broad effective lineages and no lineage monopoly;
- sufficient cumulative births, mean generation and maximum generation;
- a high living-descendant fraction;
- enough unique and effective successful parents;
- no parent dominating the reproduction window.

A burn-in tick inferred from pilot seeds applies only to future independent seeds. The pilot windows used to derive it are not reused as confirmatory selection evidence.

## GPU execution and parity

Normal runs default to `--backend auto`. A compatible CUDA/CuPy stack uses `gpu-hybrid-accelerated`; otherwise the run records a CPU fallback. Scientific use on a new target stack still requires:

```bash
make parity-gpu
```

`tests/test_parity.py` validates device stages, persistent mirrors and all checkpoint-authoritative semantic leaves. Execution provenance and parity remain separate from scientific-effect inference.

## Workflow

After metadata, entry-point, dependency or package-layout changes:

```bash
make conda-sync
```

Daily validation:

```bash
make test
make conda-check
```

Artifact validation:

```bash
make release-check
```

## Current version documents

- [Implementation report](docs/v0.68/IMPLEMENTATION_REPORT.md)
- [D3-J pilot interpretation](docs/v0.68/D3J_1200_PILOT_INTERPRETATION.md)
- [D3-K demographic source plan](docs/v0.68/DEMOGRAPHIC_SOURCE_PLAN.md)
- [Protocol audit](docs/v0.68/protocol_audit.md)
