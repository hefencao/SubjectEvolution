from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from se.cfg import load_config
from se.gpu_memory import (
    BOUNDED_CACHE_POLICY,
    UNBOUNDED_CACHE_POLICY,
    GpuMemoryPoolController,
)

ROOT = Path(__file__).resolve().parents[1]


class FakePool:
    def __init__(self, *, used: int, total: int, free_to: int | None = None) -> None:
        self.used = used
        self.total = total
        self.free_to = used if free_to is None else free_to
        self.free_calls = 0

    def used_bytes(self) -> int:
        return self.used

    def total_bytes(self) -> int:
        return self.total

    def free_all_blocks(self) -> None:
        self.free_calls += 1
        self.total = max(self.used, self.free_to)


class FakePinnedPool:
    def __init__(self) -> None:
        self.free_calls = 0
        self.blocks = 7

    def free_all_blocks(self) -> None:
        self.free_calls += 1
        self.blocks = 0

    def n_free_blocks(self) -> int:
        return self.blocks


class FakeXp:
    def __init__(self, pool: FakePool, pinned: FakePinnedPool) -> None:
        self.pool = pool
        self.pinned = pinned

    def get_default_memory_pool(self) -> FakePool:
        return self.pool

    def get_default_pinned_memory_pool(self) -> FakePinnedPool:
        return self.pinned


def test_bounded_pool_releases_only_cached_blocks() -> None:
    pool = FakePool(used=300, total=1500)
    pinned = FakePinnedPool()
    controller = GpuMemoryPoolController(
        FakeXp(pool, pinned),
        policy=BOUNDED_CACHE_POLICY,
        cache_limit_bytes=500,
        trim_period=1,
    )
    controller.begin_step()
    snapshot = controller.finish_step()
    assert pool.free_calls == 1
    assert pinned.free_calls == 1
    assert snapshot.used_bytes == 300
    assert snapshot.total_bytes == 300
    assert snapshot.cached_bytes == 0
    assert snapshot.cached_bytes_after_trim == 0
    assert snapshot.total_bytes_after_trim == 300
    assert snapshot.released_bytes_step == 1200
    assert snapshot.trimmed_step is True
    assert snapshot.trim_count == 1
    assert snapshot.peak_total_bytes == 1500


def test_bounded_pool_respects_period_and_limit() -> None:
    pool = FakePool(used=300, total=1200)
    controller = GpuMemoryPoolController(
        FakeXp(pool, FakePinnedPool()),
        policy=BOUNDED_CACHE_POLICY,
        cache_limit_bytes=500,
        trim_period=2,
    )
    controller.begin_step()
    first = controller.finish_step()
    assert first.trimmed_step is False
    assert pool.free_calls == 0
    controller.begin_step()
    second = controller.finish_step()
    assert second.trimmed_step is True
    assert pool.free_calls == 1


def test_unbounded_policy_reports_without_trimming() -> None:
    pool = FakePool(used=300, total=1500)
    controller = GpuMemoryPoolController(
        FakeXp(pool, FakePinnedPool()),
        policy=UNBOUNDED_CACHE_POLICY,
        cache_limit_bytes=0,
        trim_period=1,
    )
    controller.begin_step()
    snapshot = controller.finish_step()
    assert pool.free_calls == 0
    assert snapshot.cached_bytes == 1200
    assert snapshot.trim_count == 0


def test_numpy_like_namespace_has_zero_pool_telemetry() -> None:
    controller = GpuMemoryPoolController(object())
    assert controller.finish_step().total_bytes == 0


def test_gpu_memory_pool_config_boundaries() -> None:
    cfg = load_config(ROOT / "configs" / "mvp_d3l_gpu_scale4_regime_resolution.json")
    assert cfg.run.gpu_memory_pool_policy == BOUNDED_CACHE_POLICY
    assert cfg.run.gpu_memory_pool_cache_limit_bytes > 0
    assert cfg.run.gpu_memory_pool_trim_period == 1
    with pytest.raises(ValueError, match="cache limit"):
        GpuMemoryPoolController(object(), cache_limit_bytes=-1)
    with pytest.raises(ValueError, match="trim period"):
        GpuMemoryPoolController(object(), trim_period=0)


def test_trim_occurs_before_current_step_allocations() -> None:
    pool = FakePool(used=300, total=1500)
    controller = GpuMemoryPoolController(
        FakeXp(pool, FakePinnedPool()),
        policy=BOUNDED_CACHE_POLICY,
        cache_limit_bytes=500,
        trim_period=1,
    )
    controller.begin_step()
    assert pool.free_calls == 1
    # Simulate current-step allocations and cache growth after the safe trim boundary.
    pool.used = 700
    pool.total = 1100
    snapshot = controller.finish_step()
    assert snapshot.total_bytes_after_trim == 300
    assert snapshot.cached_bytes_after_trim == 0
    assert snapshot.used_bytes == 700
    assert snapshot.cached_bytes == 400
