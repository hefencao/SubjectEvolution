#!/usr/bin/env python3
"""Compare migrated GPU field stages against the CPU reference implementation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np

from subject_evolution.backend import BackendUnavailableError, resolve_backend
from subject_evolution.config import load_config
from subject_evolution.environment import Environment
from subject_evolution.gpu_environment import DeviceEnvironment, DeviceInformationField
from subject_evolution.information import InformationSystem


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--config", required=True, help="JSON simulation configuration")
    result.add_argument("--ticks", type=int, default=16, help="Number of fixed field updates to compare")
    result.add_argument(
        "--atol",
        type=float,
        default=5e-6,
        help="Absolute float32 comparison tolerance for multi-tick field updates",
    )
    return result


def _max_error(actual: np.ndarray, expected: np.ndarray) -> float:
    return float(np.max(np.abs(actual.astype(np.float64) - expected.astype(np.float64))))


def main() -> int:
    args = parser().parse_args()
    if args.ticks <= 0:
        raise ValueError("--ticks must be positive")
    cfg = load_config(Path(args.config))
    try:
        backend = resolve_backend("gpu")
    except BackendUnavailableError as exc:
        print(f"GPU validation unavailable: {exc}")
        return 2

    cpu_environment = Environment(cfg)
    gpu_environment = DeviceEnvironment(cfg, backend)
    cpu_field = InformationSystem(cfg)
    gpu_field = DeviceInformationField(cfg, backend)
    # Construction and initial host->device copies are not part of the update
    # profile; synchronize once before starting measured stage work.
    backend.synchronize()
    cell_count = cfg.world.grid_x * cfg.world.grid_y
    cells = np.concatenate(
        (
            np.arange(min(cell_count, 257), dtype=np.int32) % cell_count,
            np.asarray([0, 1, 1, 2, 2, 2], dtype=np.int32) % cell_count,
        )
    )
    strengths = (0.01 + (cells % 11).astype(np.float32) * 0.007).astype(np.float32)

    cpu_seconds = 0.0
    gpu_seconds = 0.0
    for tick in range(args.ticks):
        started = time.perf_counter()
        cpu_environment.update(tick)
        cpu_field.emit(tick % cpu_field.CHANNELS, cells, strengths)
        cpu_field.propagate()
        cpu_seconds += time.perf_counter() - started

        started = time.perf_counter()
        gpu_environment.update(tick)
        gpu_field.emit(tick % gpu_field.CHANNELS, cells, strengths)
        gpu_field.propagate()
        backend.synchronize()
        gpu_seconds += time.perf_counter() - started

    probe_cells = cells[: min(cells.size, 64)]
    entity_cells = np.concatenate((probe_cells[: min(probe_cells.size, 8)], np.asarray([-1], dtype=np.int32)))
    rates = np.tile(np.asarray([0.2, 0.1, 0.05, 0.02], dtype=np.float32), (probe_cells.size, 1))
    cpu_gathered = cpu_environment.resolve_harvest(probe_cells, rates)
    gpu_gathered = backend.to_numpy(gpu_environment.resolve_harvest(probe_cells, rates))
    cpu_environment.commit_harvest(probe_cells, cpu_gathered)
    gpu_environment.commit_harvest(probe_cells, gpu_gathered)
    backend.synchronize()
    (cpu_resource_gradient, cpu_hazard_gradient) = cpu_environment.gradients_for_entities(
        entity_cells, entity_cells.size
    )
    (gpu_resource_gradient, gpu_hazard_gradient) = gpu_environment.gradients_for_entities(
        entity_cells, entity_cells.size
    )
    errors = {
        "resources": _max_error(backend.to_numpy(gpu_environment.resources), cpu_environment.resources),
        "hazard": _max_error(backend.to_numpy(gpu_environment.hazard), cpu_environment.hazard),
        "information_field": _max_error(backend.to_numpy(gpu_field.field), cpu_field.field),
        "cell_values": _max_error(
            backend.to_numpy(gpu_environment.cell_values(probe_cells)), cpu_environment.cell_values(probe_cells)
        ),
        "harvest_allocation": _max_error(gpu_gathered, cpu_gathered),
        "resource_gradient_x": _max_error(backend.to_numpy(gpu_resource_gradient[0]), cpu_resource_gradient[0]),
        "resource_gradient_y": _max_error(backend.to_numpy(gpu_resource_gradient[1]), cpu_resource_gradient[1]),
        "hazard_gradient_x": _max_error(backend.to_numpy(gpu_hazard_gradient[0]), cpu_hazard_gradient[0]),
        "hazard_gradient_y": _max_error(backend.to_numpy(gpu_hazard_gradient[1]), cpu_hazard_gradient[1]),
    }
    passed = all(error <= args.atol for error in errors.values()) and np.array_equal(
        backend.to_numpy(gpu_field.age), cpu_field.age
    )
    print(
        json.dumps(
            {
                "passed": passed,
                "ticks": args.ticks,
                "atol": args.atol,
                "max_abs_error": errors,
                "cpu_seconds": cpu_seconds,
                "gpu_seconds": gpu_seconds,
                "backend": backend.name,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
