from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any
import numpy as np

from .backend import backend_from_array


class Stream(IntEnum):
    ENV_RESOURCE = 1
    ENV_CLIMATE = 2
    SIGNAL_CHANNEL = 11
    SIGNAL_DETECTION = 12
    SIGNAL_DECODING = 13
    MEMORY_NOISE = 14
    NEIGHBOR_SAMPLE = 20
    ATTENTION_SAMPLE = 21
    POLICY_ACTION = 30
    ACTION_EXECUTION = 32
    CONFLICT_RESOLUTION = 40
    REPRODUCTION_CAPACITY = 41
    REPRODUCTION = 50
    MUTATION = 51
    RELATION_UPDATE = 70
    GROUP_FORMATION = 71
    CAUSAL_INTERVENTION = 80
    AUTONOMY_RECOVERY = 81
    EVOLUTION_EVALUATION = 82
    KNOWLEDGE_SEED = 90
    KNOWLEDGE_FORGET = 91
    KNOWLEDGE_TRANSFER = 92
    KNOWLEDGE_DAMAGE = 93
    KNOWLEDGE_CHANNEL = 94


@dataclass(frozen=True)
class RandomContext:
    run_seed: int
    tick: int
    phase: int
    stream: Stream


_MASK = 0xFFFFFFFFFFFFFFFF
_C1 = 0x9E3779B97F4A7C15
_C2 = 0xBF58476D1CE4E5B9
_C3 = 0x94D049BB133111EB
_GPU_KEY_KERNEL: Any | None = None


def _any_true(xp: object, value: object) -> bool:
    """Reduce a NumPy/CuPy boolean array to a host bool for validation."""
    return bool(xp.any(value).item())


def _keys_on_backend(
    ctx: RandomContext,
    subject_ids: np.ndarray,
    draw_index: int | Any,
    xp: object,
) -> np.ndarray:
    """Construct SplitMix64 keys without moving an array between backends."""
    # CuPy otherwise evaluates every SplitMix64 xor, shift, and multiply as a
    # separate device kernel.  The fused implementation preserves the exact
    # uint64 arithmetic of the NumPy reference while reducing launch overhead
    # in field observation, partner sampling, and policy sampling.
    if callable(getattr(xp, "ElementwiseKernel", None)):
        return _gpu_keys(ctx, subject_ids, draw_index, xp)
    uint64 = xp.uint64
    ids = xp.asarray(subject_ids, dtype=np.uint64)
    x = ids.copy()
    # Counter arithmetic intentionally wraps at 64 bits.  Calculate the
    # scalar terms with Python integers first, then materialize them in the
    # selected array namespace so NumPy and CuPy use the same bit pattern.
    x ^= uint64((int(ctx.run_seed) * 0xD1342543DE82EF95) & _MASK)
    x ^= uint64((int(ctx.tick) * 0xA24BAED4963EE407) & _MASK)
    x ^= uint64((int(ctx.phase) * 0x9FB21C651E98DF25) & _MASK)
    x ^= uint64((int(ctx.stream) * 0xC13FA9A902A6328F) & _MASK)
    # A scalar draw index is the usual path.  Batched event processing also
    # needs one draw index per row; evaluating those keys together preserves
    # the exact state-free random stream without a Python loop.
    if np.isscalar(draw_index):
        x ^= uint64((int(draw_index) * 0x91E10DA5C79E7B1D) & _MASK)
    else:
        draw = xp.asarray(draw_index, dtype=xp.uint64)
        x ^= (draw * uint64(0x91E10DA5C79E7B1D)) & uint64(_MASK)
    return _mix64(x, xp)


def _gpu_keys(
    ctx: RandomContext,
    subject_ids: np.ndarray,
    draw_index: int | Any,
    xp: object,
) -> np.ndarray:
    """Fused CuPy SplitMix64 path; called only for a GPU array namespace."""
    global _GPU_KEY_KERNEL
    if _GPU_KEY_KERNEL is None:
        _GPU_KEY_KERNEL = xp.ElementwiseKernel(
            "uint64 subject_id, uint64 draw_index, uint64 seed_term, uint64 tick_term, "
            "uint64 phase_term, uint64 stream_term, uint64 draw_multiplier, "
            "uint64 mix_one, uint64 mix_two, uint64 mix_three",
            "uint64 out",
            """
                unsigned long long x = subject_id;
                x ^= seed_term;
                x ^= tick_term;
                x ^= phase_term;
                x ^= stream_term;
                x ^= draw_index * draw_multiplier;
                x += mix_one;
                x = ((x ^ (x >> 30)) * mix_two);
                x = ((x ^ (x >> 27)) * mix_three);
                out = x ^ (x >> 31);
            """,
            "se_splitmix64",
        )
    uint64 = xp.uint64
    return _GPU_KEY_KERNEL(
        xp.asarray(subject_ids, dtype=uint64),
        xp.asarray(draw_index, dtype=uint64),
        uint64((int(ctx.run_seed) * 0xD1342543DE82EF95) & _MASK),
        uint64((int(ctx.tick) * 0xA24BAED4963EE407) & _MASK),
        uint64((int(ctx.phase) * 0x9FB21C651E98DF25) & _MASK),
        uint64((int(ctx.stream) * 0xC13FA9A902A6328F) & _MASK),
        uint64(0x91E10DA5C79E7B1D),
        uint64(_C1),
        uint64(_C2),
        uint64(_C3),
    )


def _uniform01_on_backend(
    ctx: RandomContext,
    subject_ids: np.ndarray,
    draw_index: int | Any,
    xp: object,
) -> np.ndarray:
    value = _keys_on_backend(ctx, subject_ids, draw_index, xp)
    # Use the top 53 bits, matching double-precision mantissa capacity.
    return ((value >> xp.uint64(11)).astype(np.float64)) * (1.0 / (1 << 53))


def _mix64(x: np.ndarray, xp: object | None = None) -> np.ndarray:
    """SplitMix64 finalizer; deterministic and vectorizable on NumPy/CuPy."""
    if xp is None:
        xp = backend_from_array(x).xp
    uint64 = xp.uint64
    mask = uint64(_MASK)
    x = (x + uint64(_C1)) & mask
    x = ((x ^ (x >> uint64(30))) * uint64(_C2)) & mask
    x = ((x ^ (x >> uint64(27))) * uint64(_C3)) & mask
    return x ^ (x >> uint64(31))


def keys(ctx: RandomContext, subject_ids: np.ndarray, draw_index: int | Any = 0) -> np.ndarray:
    """Return stateless 64-bit keys on the backend that owns ``subject_ids``.

    A NumPy subject-id array keeps the CPU reference path.  A CuPy subject-id
    array produces a CuPy array using the same counter fields and SplitMix64
    operations, so key values are bit-for-bit comparable across the two
    backends.
    """
    xp = backend_from_array(subject_ids).xp
    return _keys_on_backend(ctx, subject_ids, draw_index, xp)


def uniform01(ctx: RandomContext, subject_ids: np.ndarray, draw_index: int | Any = 0) -> np.ndarray:
    """Sample ``[0, 1)`` uniformly on the backend that owns ``subject_ids``."""
    xp = backend_from_array(subject_ids).xp
    return _uniform01_on_backend(ctx, subject_ids, draw_index, xp)


def bernoulli(
    ctx: RandomContext,
    subject_ids: np.ndarray,
    p: float | np.ndarray,
    draw_index: int | Any = 0,
    *,
    validate_probability: bool = True,
) -> np.ndarray:
    """Draw Bernoulli outcomes without mutable CPU or GPU RNG state."""
    xp = backend_from_array(subject_ids).xp
    prob = xp.asarray(p, dtype=np.float64)
    if validate_probability and _any_true(xp, ~xp.isfinite(prob) | (prob < 0.0) | (prob > 1.0)):
        raise ValueError("Bernoulli probability must be in [0, 1]")
    return _uniform01_on_backend(ctx, subject_ids, draw_index, xp) < prob


def normal(
    ctx: RandomContext,
    subject_ids: np.ndarray,
    mean: float | np.ndarray = 0.0,
    stddev: float | np.ndarray = 1.0,
    draw_index: int | Any = 0,
    *,
    validate_stddev: bool = True,
) -> np.ndarray:
    """Draw Box--Muller normals without mutable CPU or GPU RNG state."""
    xp = backend_from_array(subject_ids).xp
    std = xp.asarray(stddev, dtype=np.float64)
    if validate_stddev and _any_true(xp, ~xp.isfinite(std) | (std < 0)):
        raise ValueError("Normal stddev cannot be negative")
    u1 = xp.clip(_uniform01_on_backend(ctx, subject_ids, draw_index, xp), 1e-12, 1.0)
    next_draw = (
        int(draw_index) + 1
        if np.isscalar(draw_index)
        else xp.asarray(draw_index, dtype=xp.uint64) + xp.uint64(1)
    )
    u2 = _uniform01_on_backend(ctx, subject_ids, next_draw, xp)
    z = xp.sqrt(-2.0 * xp.log(u1)) * xp.cos(2.0 * np.pi * u2)
    return xp.asarray(mean, dtype=np.float64) + std * z


def categorical_from_logits(
    ctx: RandomContext,
    subject_ids: np.ndarray,
    logits: np.ndarray,
    temperature: float,
    mask: np.ndarray | None = None,
    draw_index: int | Any = 0,
    *,
    validate_mask: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample one categorical action per row, returning action, probability and entropy."""
    if not np.isfinite(temperature) or temperature <= 0:
        raise ValueError("temperature must be positive")
    xp = backend_from_array(subject_ids).xp
    values = xp.asarray(logits, dtype=np.float64) / temperature
    if values.ndim != 2:
        raise ValueError("logits must be a 2-D array")
    ids = xp.asarray(subject_ids, dtype=np.uint64)
    if ids.ndim != 1 or ids.shape[0] != values.shape[0]:
        raise ValueError("subject_ids must be a 1-D array with one ID per logits row")
    if mask is not None:
        valid = xp.asarray(mask, dtype=bool)
        if valid.shape != values.shape:
            raise ValueError("mask shape must match logits")
        if validate_mask and _any_true(xp, ~valid.any(axis=1)):
            raise ValueError("every row must contain at least one valid action")
        values = xp.where(valid, values, -np.inf)
    max_values = xp.max(values, axis=1, keepdims=True)
    exp_values = xp.exp(values - max_values)
    probs = exp_values / exp_values.sum(axis=1, keepdims=True)
    cdf = xp.cumsum(probs, axis=1)
    u = _uniform01_on_backend(ctx, ids, draw_index, xp)
    action = (cdf < u[:, None]).sum(axis=1).astype(np.int16)
    selected = probs[xp.arange(probs.shape[0]), action]
    entropy = -(probs * xp.log(xp.clip(probs, 1e-12, 1.0))).sum(axis=1)
    return action, selected.astype(np.float32), entropy.astype(np.float32)
