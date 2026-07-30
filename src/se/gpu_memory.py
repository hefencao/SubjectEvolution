"""Bounded GPU allocator-cache management for long hybrid runs.

CuPy's default memory pool intentionally retains freed blocks.  That improves
steady-shape workloads, but a population whose active batch grows every tick
can leave a staircase of smaller cached blocks behind.  This module bounds only
that *unused cache*.  It never caps live device arrays, changes simulation
state, or triggers a backend fallback.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

BOUNDED_CACHE_POLICY = "bounded-cache-v1"
UNBOUNDED_CACHE_POLICY = "unbounded-default-v1"
SUPPORTED_POLICIES = {BOUNDED_CACHE_POLICY, UNBOUNDED_CACHE_POLICY}


@dataclass(frozen=True)
class GpuMemoryPoolSnapshot:
    """One end-of-step allocator snapshot."""

    used_bytes: int = 0
    total_bytes: int = 0
    cached_bytes: int = 0
    total_bytes_after_trim: int = 0
    cached_bytes_after_trim: int = 0
    peak_used_bytes: int = 0
    peak_total_bytes: int = 0
    trim_count: int = 0
    trimmed_step: bool = False
    released_bytes_step: int = 0
    pinned_free_blocks: int = 0


class GpuMemoryPoolController:
    """Trim only unused default-pool blocks at deterministic step boundaries."""

    def __init__(
        self,
        xp: Any,
        *,
        policy: str = BOUNDED_CACHE_POLICY,
        cache_limit_bytes: int = 512 * 1024 * 1024,
        trim_period: int = 1,
    ) -> None:
        if policy not in SUPPORTED_POLICIES:
            raise ValueError(f"unsupported GPU memory-pool policy: {policy}")
        if cache_limit_bytes < 0:
            raise ValueError("GPU memory-pool cache limit must be non-negative")
        if trim_period <= 0:
            raise ValueError("GPU memory-pool trim period must be positive")
        self.policy = policy
        self.cache_limit_bytes = int(cache_limit_bytes)
        self.trim_period = int(trim_period)
        self._step_count = 0
        self._trim_count = 0
        self._peak_used_bytes = 0
        self._peak_total_bytes = 0
        self._step_open = False
        self._pending_trimmed = False
        self._pending_released_bytes = 0
        self._pending_total_after_trim = 0
        self._pending_cached_after_trim = 0
        get_pool = getattr(xp, "get_default_memory_pool", None)
        get_pinned = getattr(xp, "get_default_pinned_memory_pool", None)
        self._pool = get_pool() if callable(get_pool) else None
        self._pinned_pool = get_pinned() if callable(get_pinned) else None

    @staticmethod
    def _value(pool: Any, name: str) -> int:
        method = getattr(pool, name, None)
        return int(method()) if callable(method) else 0

    def begin_step(self) -> None:
        """Trim stale cache after the previous step frame has exited.

        The simulation calls this before allocating the next step's transient
        arrays.  At this boundary, local arrays from the preceding ``step``
        call have lost their Python references, while persistent device state
        remains live and cannot be released by ``free_all_blocks``.
        """

        if self._step_open:
            raise RuntimeError("GPU memory-pool step already open")
        self._step_open = True
        self._step_count += 1
        self._pending_trimmed = False
        self._pending_released_bytes = 0
        self._pending_total_after_trim = 0
        self._pending_cached_after_trim = 0
        if self._pool is None:
            return

        used_before = self._value(self._pool, "used_bytes")
        total_before = self._value(self._pool, "total_bytes")
        cached_before = max(total_before - used_before, 0)
        self._peak_used_bytes = max(self._peak_used_bytes, used_before)
        self._peak_total_bytes = max(self._peak_total_bytes, total_before)

        due = self._step_count % self.trim_period == 0
        if (
            self.policy == BOUNDED_CACHE_POLICY
            and due
            and cached_before > self.cache_limit_bytes
        ):
            free_all = getattr(self._pool, "free_all_blocks", None)
            if callable(free_all):
                free_all()
            pinned_free_all = getattr(self._pinned_pool, "free_all_blocks", None)
            if callable(pinned_free_all):
                pinned_free_all()
            total_after = self._value(self._pool, "total_bytes")
            released = max(total_before - total_after, 0)
            self._pending_trimmed = True
            self._pending_released_bytes = released
            self._trim_count += 1

        used_after = self._value(self._pool, "used_bytes")
        total_after = self._value(self._pool, "total_bytes")
        self._pending_total_after_trim = total_after
        self._pending_cached_after_trim = max(total_after - used_after, 0)
        self._peak_used_bytes = max(self._peak_used_bytes, used_after)
        self._peak_total_bytes = max(self._peak_total_bytes, total_after)

    def finish_step(self) -> GpuMemoryPoolSnapshot:
        """Measure end-of-step usage and attach the start-boundary trim event."""

        # Preserve direct-call compatibility for diagnostics and unit tests.
        # Production runtime opens the boundary before any step allocations.
        if not self._step_open:
            self.begin_step()
        if self._pool is None:
            self._step_open = False
            return GpuMemoryPoolSnapshot()

        used = self._value(self._pool, "used_bytes")
        total = self._value(self._pool, "total_bytes")
        cached = max(total - used, 0)
        self._peak_used_bytes = max(self._peak_used_bytes, used)
        self._peak_total_bytes = max(self._peak_total_bytes, total)
        pinned_blocks = self._value(self._pinned_pool, "n_free_blocks")
        snapshot = GpuMemoryPoolSnapshot(
            used_bytes=used,
            total_bytes=total,
            cached_bytes=cached,
            total_bytes_after_trim=self._pending_total_after_trim,
            cached_bytes_after_trim=self._pending_cached_after_trim,
            peak_used_bytes=self._peak_used_bytes,
            peak_total_bytes=self._peak_total_bytes,
            trim_count=self._trim_count,
            trimmed_step=self._pending_trimmed,
            released_bytes_step=self._pending_released_bytes,
            pinned_free_blocks=pinned_blocks,
        )
        self._step_open = False
        return snapshot


__all__ = [
    "BOUNDED_CACHE_POLICY",
    "UNBOUNDED_CACHE_POLICY",
    "SUPPORTED_POLICIES",
    "GpuMemoryPoolController",
    "GpuMemoryPoolSnapshot",
]
