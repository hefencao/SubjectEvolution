"""Summarize physical heterogeneity and realized within-group division evidence.

Exploratory mode is parameter-debugging only and can never authorize an
environment-plurality claim. Formal mode requires independent multi-seed runs
and treats group labels without persistent internal functional differentiation
as below the requested environment threshold.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "structured-environment-division-summary-v1"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _run_key(path: Path, root: Path) -> str:
    try:
        relative = path.parent.relative_to(root)
        return str(relative) or path.parent.name
    except ValueError:
        return path.parent.name


def _atlas_metrics(path: Path | None) -> dict[str, float]:
    if path is None or not path.exists():
        return {
            "resource_field_effective_dimensions": 0.0,
            "resource_channel_mean_abs_correlation": 1.0,
            "region_signature_effective_dimensions": 0.0,
            "region_signature_max_pairwise_distance": 0.0,
        }
    payload = _load(path)
    scales = (payload.get("last") or {}).get("scales") or []
    if not isinstance(scales, list) or not scales:
        return {
            "resource_field_effective_dimensions": 0.0,
            "resource_channel_mean_abs_correlation": 1.0,
            "region_signature_effective_dimensions": 0.0,
            "region_signature_max_pairwise_distance": 0.0,
        }
    return {
        "resource_field_effective_dimensions": max(
            float(row.get("resource_field_effective_dimensions", 0.0))
            for row in scales
        ),
        "resource_channel_mean_abs_correlation": min(
            float(row.get("resource_channel_mean_abs_correlation", 1.0))
            for row in scales
        ),
        "region_signature_effective_dimensions": max(
            float(row.get("region_signature_effective_dimensions", 0.0))
            for row in scales
        ),
        "region_signature_max_pairwise_distance": max(
            float(row.get("region_signature_max_pairwise_distance", 0.0))
            for row in scales
        ),
    }


def build_report(
    *,
    source_root: str | Path,
    mode: str,
    required_seed_count: int,
) -> dict[str, Any]:
    root = Path(source_root)
    if mode not in {"exploratory", "formal"}:
        raise ValueError("mode must be exploratory or formal")
    if int(required_seed_count) <= 0:
        raise ValueError("required_seed_count must be positive")
    if mode == "formal" and int(required_seed_count) < 3:
        raise ValueError("formal environment structure evidence requires at least three seeds")

    group_files = sorted(root.rglob("group_function_summary.json"))
    runs: list[dict[str, Any]] = []
    for group_path in group_files:
        group = _load(group_path)
        atlas_path = group_path.with_name("environment_atlas_summary.json")
        summary_path = group_path.with_name("summary.json")
        config_path = group_path.with_name("resolved_config.json")
        atlas = _atlas_metrics(atlas_path if atlas_path.exists() else None)
        runtime = _load(summary_path) if summary_path.exists() else {}
        config = _load(config_path) if config_path.exists() else {}
        initial_population = int(
            config.get("world", {}).get(
                "initial_entities",
                config.get("entities", {}).get("initial_count", 0),
            )
        )
        alive = int(runtime.get("alive", 0))
        births_per_initial = float(
            runtime.get("cumulative_births_per_initial", 0.0)
        )
        descendant_fraction = float(
            runtime.get("descendant_alive_fraction", 0.0)
        )
        persistent = (
            group.get("persistent_division_candidate_lineages")
            or group.get("persistent_division_candidate_tokens")
            or {}
        )
        persistent_count = int(
            group.get(
                "persistent_division_lineage_count",
                group.get("persistent_division_candidate_count", len(persistent)),
            )
        )
        max_streak = max(
            [int(value) for value in persistent.values()] or
            [int(value) for value in (group.get("max_candidate_streak_by_lineage") or {}).values()] or
            [int(value) for value in (group.get("max_candidate_streak_by_token") or {}).values()] or
            [0]
        )
        max_simultaneous = int(group.get("max_candidate_groups_in_window", 0))
        exchange_total = sum(
            float(value) for value in group.get("internal_raw_exchange_total", [0.0] * 4)
        )
        physical_ready = bool(
            atlas["resource_field_effective_dimensions"] >= 1.75
            and atlas["region_signature_effective_dimensions"] >= 1.5
            and atlas["region_signature_max_pairwise_distance"] >= 0.20
        )
        division_ready = bool(
            persistent_count >= 2
            and max_streak >= 2
            and max_simultaneous >= 2
            and exchange_total > 1.0e-6
        )
        population_ready = bool(
            initial_population > 0
            and alive >= 0.5 * initial_population
            and births_per_initial >= 0.5
            and descendant_fraction >= 0.30
        )
        runs.append(
            {
                "run": _run_key(group_path, root),
                "group_function_summary": str(group_path),
                "environment_atlas_summary": str(atlas_path) if atlas_path.exists() else None,
                "runtime_summary": str(summary_path) if summary_path.exists() else None,
                **atlas,
                "initial_population": initial_population,
                "alive": alive,
                "cumulative_births_per_initial": births_per_initial,
                "descendant_alive_fraction": descendant_fraction,
                "population_substrate_ready": population_ready,
                "physical_heterogeneity_ready": physical_ready,
                "persistent_division_candidate_count": persistent_count,
                "max_division_candidate_streak": max_streak,
                "max_simultaneous_division_candidate_groups": max_simultaneous,
                "internal_raw_exchange_total": exchange_total,
                "within_group_division_ready": division_ready,
            }
        )

    observed = len(runs)
    complete = observed == int(required_seed_count)
    physical_count = sum(bool(row["physical_heterogeneity_ready"]) for row in runs)
    population_count = sum(bool(row["population_substrate_ready"]) for row in runs)
    division_count = sum(bool(row["within_group_division_ready"]) for row in runs)
    multi_group_count = sum(
        int(row["max_simultaneous_division_candidate_groups"] >= 2)
        for row in runs
    )
    if observed == 0:
        stage = "insufficient-runtime-output"
    elif population_count < observed:
        stage = "population-substrate-insufficient"
    elif physical_count < observed:
        stage = "physical-heterogeneity-insufficient"
    elif division_count == 0:
        stage = "group-labels-without-within-group-division"
    elif division_count < observed:
        stage = "non-replicated-within-group-division-candidate"
    elif multi_group_count == 0:
        stage = "replicated-division-without-multiple-structured-groups"
    else:
        stage = "replicated-structured-group-candidates"

    formal_threshold = bool(
        mode == "formal"
        and complete
        and population_count == observed
        and physical_count == observed
        and division_count == observed
        and multi_group_count == observed
    )
    return {
        "schema": SCHEMA,
        "mode": mode,
        "source_root": str(root),
        "required_seed_count": int(required_seed_count),
        "observed_seed_count": observed,
        "seed_set_complete": complete,
        "runs": runs,
        "physical_heterogeneity_ready_seed_count": physical_count,
        "population_substrate_ready_seed_count": population_count,
        "within_group_division_ready_seed_count": division_count,
        "multiple_structured_groups_seed_count": multi_group_count,
        "environment_maturity_stage": stage,
        "environment_plurality_threshold_reached": formal_threshold,
        "evidence_class": (
            "formal-multi-seed-structured-environment-evidence"
            if formal_threshold
            else "parameter-debug-only"
            if mode == "exploratory"
            else "formal-threshold-not-reached"
        ),
        "authorization": {
            "continue_environment_parameter_debugging": not formal_threshold,
            "environment_plurality_claim": formal_threshold,
            "single_run_gene_audit": False,
            "formal_gene_retention_audit": False,
            "selection_or_adaptation_claim": False,
        },
        "thresholds": {
            "formal_minimum_seed_count": 3,
            "resource_field_effective_dimensions_min": 1.75,
            "region_signature_effective_dimensions_min": 1.5,
            "region_signature_max_pairwise_distance_min": 0.20,
            "persistent_division_candidate_windows_min": 2,
            "all_formal_seeds_require_division": True,
            "alive_fraction_to_initial_min": 0.5,
            "cumulative_births_per_initial_min": 0.5,
            "descendant_alive_fraction_min": 0.30,
            "persistent_division_candidate_groups_min_per_seed": 2,
            "all_formal_seeds_require_multiple_division_groups": True,
        },
        "interpretation_boundary": (
            "The threshold requires replicated physical heterogeneity, raw exchange and "
            "persistent within-group functional differentiation. It does not establish "
            "fixed roles, adaptation, selection, subjecthood, or permission for a single-round gene audit."
        ),
        "next_action": (
            "freeze-the-structured-environment-and-design-a-separate-multi-generation-genetic-study"
            if formal_threshold
            else "adjust-only-shared-environment-exchange-or-processing-parameters-and-rerun-probes"
        ),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--mode", choices=["exploratory", "formal"], required=True)
    parser.add_argument("--required-seed-count", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    report = build_report(
        source_root=args.source_root,
        mode=args.mode,
        required_seed_count=args.required_seed_count,
    )
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
