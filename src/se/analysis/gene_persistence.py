"""Panel-level screen for inherited coordinates that thin, concentrate, or vanish.

This is a retention scan, not a causal module audit.  It reads trusted thin
checkpoints produced by the simulator, compares the first and final registered
checkpoint within each independent seed, and only reports cross-seed persistence.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from se.cfg import load_config
from se.differentiation.capacity import CAPACITY_TRAIT_NAMES, capacity_gene_count
from se.differentiation.functional import (
    REGULATORY_OUTPUT_NAMES,
    functional_module_auxiliary_output_count,
    functional_module_coupling_count,
    functional_module_gene_count,
    functional_module_genes_per_module,
    functional_module_input_count,
)
from se.differentiation.physiology import physiology_gene_count, physiology_gene_names
from se.policy import Action, ParametricPolicy

SCHEMA = "gene-persistence-panel-v1"
ACTIVE_ABS_THRESHOLD = 0.10
LOST_ACTIVE_FRACTION = 0.05
THIN_ACTIVE_FRACTION = 0.20
LOW_STD = 0.02
CONCENTRATION_RATIO = 0.20


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _labels(cfg: Any) -> tuple[list[str], list[str]]:
    size = ParametricPolicy.genome_size_for_config(cfg)
    names = [f"gene[{i}]" for i in range(size)]
    blocks = ["unassigned"] * size

    morphology_names = [
        "sensor_quality", "resource_affinity_0", "resource_affinity_1", "resource_affinity_2",
        "resource_affinity_3", "movement_speed", "reproduction_investment", "resource_sensing_radius",
    ]
    for i in range(ParametricPolicy.MORPHOLOGY_TRAITS):
        names[i] = f"morphology.{morphology_names[i]}"
        blocks[i] = "morphology"

    cursor = ParametricPolicy.STRATEGY_START
    for action in Action:
        for feature in ParametricPolicy.FEATURE_NAMES:
            names[cursor] = f"strategy.{action.name.lower()}.{feature}"
            blocks[cursor] = "strategy"
            cursor += 1

    outcome_names = ("energy", "integrity", "material", "information", "fertility")
    for i, name in enumerate(outcome_names, start=ParametricPolicy.KNOWLEDGE_PREFERENCE_START):
        names[i] = f"knowledge.outcome_preference.{name}"
        blocks[i] = "knowledge_preferences"
    names[ParametricPolicy.KNOWLEDGE_USE_STRENGTH_INDEX] = "knowledge.use_strength"
    blocks[ParametricPolicy.KNOWLEDGE_USE_STRENGTH_INDEX] = "knowledge_preferences"

    core_stop = ParametricPolicy.capacity_gene_start(cfg)
    latent_start = ParametricPolicy.LATENT_ROUTER_START
    wm_start = ParametricPolicy.working_memory_gene_start(cfg)
    sparse_start = ParametricPolicy.sparse_selection_gene_start(cfg)
    for i in range(latent_start, wm_start):
        names[i] = f"latent_router[{i-latent_start}]"; blocks[i] = "latent_router"
    for i in range(wm_start, sparse_start):
        names[i] = f"working_memory_router[{i-wm_start}]"; blocks[i] = "working_memory_router"
    for i in range(sparse_start, core_stop):
        names[i] = f"sparse_selection[{i-sparse_start}]"; blocks[i] = "sparse_selection"

    capacity_start = ParametricPolicy.capacity_gene_start(cfg)
    for offset, name in enumerate(CAPACITY_TRAIT_NAMES):
        names[capacity_start + offset] = f"capacity.{name}"
        blocks[capacity_start + offset] = "capacity"

    functional_start = ParametricPolicy.functional_module_gene_start(cfg)
    per_module = functional_module_genes_per_module(cfg)
    input_count = functional_module_input_count(cfg)
    aux_count = functional_module_auxiliary_output_count(cfg)
    output_names = list(REGULATORY_OUTPUT_NAMES[:aux_count])
    for module in range(int(cfg.functional_modules.module_count)):
        base = functional_start + module * per_module
        names[base] = f"functional.module_{module}.expression_gate"; blocks[base] = "functional_modules"
        for j in range(input_count):
            names[base + 1 + j] = f"functional.module_{module}.input_{j}"; blocks[base + 1 + j] = "functional_modules"
        bias = base + 1 + input_count
        names[bias] = f"functional.module_{module}.bias"; blocks[bias] = "functional_modules"
        out = bias + 1
        for j in range(4):
            names[out + j] = f"functional.module_{module}.harvest_{j}"; blocks[out + j] = "functional_modules"
        for j in range(aux_count):
            label = output_names[j] if j < len(output_names) else f"aux_{j}"
            names[out + 4 + j] = f"functional.module_{module}.{label}"; blocks[out + 4 + j] = "functional_modules"
    coupling_start = functional_start + int(cfg.functional_modules.module_count) * per_module
    c = 0
    for target in range(1, int(cfg.functional_modules.module_count)):
        for source in range(target):
            names[coupling_start + c] = f"functional.coupling.{source}_to_{target}"
            blocks[coupling_start + c] = "functional_coupling"
            c += 1
    if c != functional_module_coupling_count(cfg):
        raise RuntimeError("functional coupling label layout drifted")

    physiology_start = ParametricPolicy.physiology_gene_start(cfg)
    physiology_names = physiology_gene_names(cfg)
    count = physiology_gene_count(cfg)
    for offset in range(count):
        label = physiology_names[offset]
        names[physiology_start + offset] = f"physiology.{label}"
        blocks[physiology_start + offset] = "physiology"
    if len(names) != size or any(block == "unassigned" for block in blocks):
        missing = [i for i, block in enumerate(blocks) if block == "unassigned"][:10]
        raise RuntimeError(f"genome label layout incomplete: {missing}")
    return names, blocks


def _checkpoint_stats(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as data:
        genotype = np.asarray(data["genotype"], dtype=np.float64)
        generation = np.asarray(data["generation"], dtype=np.int64)
        tick = int(np.asarray(data["tick"]).reshape(-1)[0])
    if genotype.ndim != 2 or genotype.shape[0] != generation.size:
        raise ValueError(f"invalid checkpoint genotype/generation shapes: {path}")
    active = np.abs(genotype) >= ACTIVE_ABS_THRESHOLD
    descendant = generation > 0
    descendant_genotype = genotype[descendant]
    return {
        "tick": tick,
        "alive": int(genotype.shape[0]),
        "descendants": int(descendant.sum()),
        "max_generation": int(generation.max()) if generation.size else 0,
        "mean": genotype.mean(axis=0),
        "std": genotype.std(axis=0),
        "mean_abs": np.abs(genotype).mean(axis=0),
        "active_fraction": active.mean(axis=0),
        "descendant_active_fraction": (
            (np.abs(descendant_genotype) >= ACTIVE_ABS_THRESHOLD).mean(axis=0)
            if descendant_genotype.size else np.zeros(genotype.shape[1], dtype=np.float64)
        ),
    }


def _seed_status(reference: dict[str, Any], final: dict[str, Any], index: int) -> str:
    ref_active = float(reference["active_fraction"][index])
    final_active = float(final["active_fraction"][index])
    final_std = float(final["std"][index])
    diversity_ratio = final_std / max(float(reference["std"][index]), LOW_STD)
    active_ratio = final_active / max(ref_active, LOST_ACTIVE_FRACTION)
    if final_active <= LOST_ACTIVE_FRACTION and final_std <= LOW_STD:
        return "lost"
    if (final_active <= THIN_ACTIVE_FRACTION and active_ratio <= 0.40) or (
        diversity_ratio <= CONCENTRATION_RATIO and final_active < 0.40
    ):
        return "thinned"
    if diversity_ratio <= CONCENTRATION_RATIO:
        return "concentrated"
    return "retained"


def build_report(*, source_root: str | Path, config: str | Path, health_report: str | Path | None = None) -> dict[str, Any]:
    root = Path(source_root)
    cfg = load_config(config)
    names, blocks = _labels(cfg)
    health = _load_json(health_report) if health_report is not None else None
    eligible = bool(health and health.get("ready"))
    seed_reports: list[dict[str, Any]] = []
    per_gene_seed: list[list[dict[str, Any]]] = [[] for _ in names]
    for seed_dir in sorted(root.glob("seed_*")):
        checkpoints = sorted(seed_dir.glob("checkpoint_*.npz"))
        if len(checkpoints) < 2:
            raise ValueError(f"seed requires at least two thin checkpoints: {seed_dir}")
        reference = _checkpoint_stats(checkpoints[0])
        final = _checkpoint_stats(checkpoints[-1])
        if len(reference["mean"]) != len(names) or len(final["mean"]) != len(names):
            raise ValueError(f"checkpoint genome size does not match config: {seed_dir}")
        seed = int(seed_dir.name.split("_", 1)[1])
        seed_reports.append({
            "seed": seed,
            "reference_tick": reference["tick"],
            "final_tick": final["tick"],
            "final_alive": final["alive"],
            "final_descendants": final["descendants"],
            "final_mean_generation": float(_load_json(seed_dir / "summary.json").get("mean_generation", 0.0)),
            "final_max_generation": final["max_generation"],
        })
        for i in range(len(names)):
            per_gene_seed[i].append({
                "seed": seed,
                "status": _seed_status(reference, final, i),
                "reference_std": float(reference["std"][i]),
                "final_std": float(final["std"][i]),
                "reference_active_fraction": float(reference["active_fraction"][i]),
                "final_active_fraction": float(final["active_fraction"][i]),
                "final_descendant_active_fraction": float(final["descendant_active_fraction"][i]),
                "final_mean": float(final["mean"][i]),
                "final_mean_abs": float(final["mean_abs"][i]),
            })
    if not seed_reports:
        raise ValueError(f"no seed directories found under {root}")
    quorum = math.floor(len(seed_reports) / 2) + 1
    genes: list[dict[str, Any]] = []
    block_status: dict[str, Counter[str]] = defaultdict(Counter)
    for i, observations in enumerate(per_gene_seed):
        counts = Counter(item["status"] for item in observations)
        if counts["lost"] >= quorum:
            status = "lost"
        elif counts["thinned"] + counts["lost"] >= quorum:
            status = "thinned"
        elif counts["concentrated"] >= quorum:
            status = "concentrated"
        else:
            status = "retained"
        block_status[blocks[i]][status] += 1
        genes.append({
            "index": i,
            "name": names[i],
            "block": blocks[i],
            "status": status,
            "seed_status_counts": dict(sorted(counts.items())),
            "equal_seed_final_active_fraction": float(np.mean([o["final_active_fraction"] for o in observations])),
            "equal_seed_final_descendant_active_fraction": float(np.mean([o["final_descendant_active_fraction"] for o in observations])),
            "equal_seed_final_std": float(np.mean([o["final_std"] for o in observations])),
            "equal_seed_final_mean_abs": float(np.mean([o["final_mean_abs"] for o in observations])),
            "seeds": observations,
        })
    status_counts = Counter(gene["status"] for gene in genes)
    interpretation = (
        "sample-ineligible-for-gene-persistence-interpretation"
        if not eligible else "retention-screen-only-no-causal-effect-claim"
    )
    return {
        "schema": SCHEMA,
        "source_root": str(root),
        "config": str(config),
        "health_report": str(health_report) if health_report is not None else None,
        "sample_eligible": eligible,
        "interpretation": interpretation,
        "thresholds": {
            "active_abs": ACTIVE_ABS_THRESHOLD,
            "lost_active_fraction": LOST_ACTIVE_FRACTION,
            "thin_active_fraction": THIN_ACTIVE_FRACTION,
            "low_std": LOW_STD,
            "concentration_ratio": CONCENTRATION_RATIO,
            "cross_seed_quorum": quorum,
        },
        "seed_count": len(seed_reports),
        "seeds": seed_reports,
        "genome_size": len(genes),
        "status_counts": dict(sorted(status_counts.items())),
        "block_status_counts": {block: dict(sorted(counts.items())) for block, counts in sorted(block_status.items())},
        "flagged_genes": [gene for gene in genes if gene["status"] != "retained"],
        "genes": genes,
        "causal_effect_claim_authorized": False,
        "adjustment_rule": "Only cross-seed lost/thinned coordinates or blocks with matching low expression/use evidence are candidates for later shared-physics or cost adjustment.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Gene persistence panel",
        "",
        f"- sample eligible: **{report['sample_eligible']}**",
        f"- interpretation: `{report['interpretation']}`",
        f"- seeds: {report['seed_count']}",
        f"- genome coordinates: {report['genome_size']}",
        f"- status counts: `{report['status_counts']}`",
        "",
        "## Blocks",
        "",
        "| block | retained | concentrated | thinned | lost |",
        "|---|---:|---:|---:|---:|",
    ]
    for block, counts in report["block_status_counts"].items():
        lines.append(f"| {block} | {counts.get('retained',0)} | {counts.get('concentrated',0)} | {counts.get('thinned',0)} | {counts.get('lost',0)} |")
    lines += ["", "## Flagged coordinates", "", "| index | name | block | status | active fraction | descendant active fraction | std |", "|---:|---|---|---|---:|---:|---:|"]
    flagged = sorted(report["flagged_genes"], key=lambda g: ({"lost":0,"thinned":1,"concentrated":2}.get(g["status"],3), g["index"]))
    for gene in flagged[:100]:
        lines.append("| {index} | `{name}` | {block} | {status} | {active:.4f} | {desc:.4f} | {std:.4f} |".format(
            index=gene["index"], name=gene["name"], block=gene["block"], status=gene["status"],
            active=gene["equal_seed_final_active_fraction"], desc=gene["equal_seed_final_descendant_active_fraction"], std=gene["equal_seed_final_std"]))
    if len(flagged) > 100:
        lines.append(f"\nFull JSON contains all {len(flagged)} flagged coordinates.")
    lines += ["", "> This is a persistence screen. Concentration, thinning, or loss is not by itself evidence of benefit, harm, selection, or ecological function.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Screen a multi-seed integrated panel for inherited coordinates that thin, concentrate, or disappear.")
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--health-report")
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-ineligible", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(source_root=args.source_root, config=args.config, health_report=args.health_report)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"sample_eligible": report["sample_eligible"], "flagged": len(report["flagged_genes"]), "output": str(output)}, ensure_ascii=False))
    if not report["sample_eligible"] and not args.allow_ineligible:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
