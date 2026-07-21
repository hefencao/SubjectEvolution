from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import numpy as np


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
    REPRODUCTION = 50
    MUTATION = 51
    RELATION_UPDATE = 70
    GROUP_FORMATION = 71
    CAUSAL_INTERVENTION = 80


@dataclass(frozen=True)
class RandomContext:
    run_seed: int
    tick: int
    phase: int
    stream: Stream


_MASK = np.uint64(0xFFFFFFFFFFFFFFFF)
_C1 = np.uint64(0x9E3779B97F4A7C15)
_C2 = np.uint64(0xBF58476D1CE4E5B9)
_C3 = np.uint64(0x94D049BB133111EB)


def _mix64(x: np.ndarray) -> np.ndarray:
    """SplitMix64 finalizer; deterministic and vectorizable."""
    x = (x + _C1) & _MASK
    x = ((x ^ (x >> np.uint64(30))) * _C2) & _MASK
    x = ((x ^ (x >> np.uint64(27))) * _C3) & _MASK
    return x ^ (x >> np.uint64(31))


def keys(ctx: RandomContext, subject_ids: np.ndarray, draw_index: int = 0) -> np.ndarray:
    ids = np.asarray(subject_ids, dtype=np.uint64)
    x = ids.copy()
    # Counter arithmetic intentionally wraps at 64 bits; compute with Python ints
    # to avoid NumPy overflow warnings while preserving exact modulo semantics.
    x ^= np.uint64((int(ctx.run_seed) * 0xD1342543DE82EF95) & 0xFFFFFFFFFFFFFFFF)
    x ^= np.uint64((int(ctx.tick) * 0xA24BAED4963EE407) & 0xFFFFFFFFFFFFFFFF)
    x ^= np.uint64((int(ctx.phase) * 0x9FB21C651E98DF25) & 0xFFFFFFFFFFFFFFFF)
    x ^= np.uint64((int(ctx.stream) * 0xC13FA9A902A6328F) & 0xFFFFFFFFFFFFFFFF)
    x ^= np.uint64((int(draw_index) * 0x91E10DA5C79E7B1D) & 0xFFFFFFFFFFFFFFFF)
    return _mix64(x)


def uniform01(ctx: RandomContext, subject_ids: np.ndarray, draw_index: int = 0) -> np.ndarray:
    value = keys(ctx, subject_ids, draw_index)
    # Use the top 53 bits, matching double-precision mantissa capacity.
    return ((value >> np.uint64(11)).astype(np.float64)) * (1.0 / (1 << 53))


def bernoulli(ctx: RandomContext, subject_ids: np.ndarray, p: float | np.ndarray, draw_index: int = 0) -> np.ndarray:
    prob = np.asarray(p, dtype=np.float64)
    if np.any((prob < 0.0) | (prob > 1.0)):
        raise ValueError("Bernoulli probability must be in [0, 1]")
    return uniform01(ctx, subject_ids, draw_index) < prob


def normal(
    ctx: RandomContext,
    subject_ids: np.ndarray,
    mean: float | np.ndarray = 0.0,
    stddev: float | np.ndarray = 1.0,
    draw_index: int = 0,
) -> np.ndarray:
    std = np.asarray(stddev, dtype=np.float64)
    if np.any(std < 0):
        raise ValueError("Normal stddev cannot be negative")
    u1 = np.clip(uniform01(ctx, subject_ids, draw_index), 1e-12, 1.0)
    u2 = uniform01(ctx, subject_ids, draw_index + 1)
    z = np.sqrt(-2.0 * np.log(u1)) * np.cos(2.0 * np.pi * u2)
    return np.asarray(mean, dtype=np.float64) + std * z


def categorical_from_logits(
    ctx: RandomContext,
    subject_ids: np.ndarray,
    logits: np.ndarray,
    temperature: float,
    mask: np.ndarray | None = None,
    draw_index: int = 0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample one categorical action per row, returning action, probability and entropy."""
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    values = np.asarray(logits, dtype=np.float64) / temperature
    if values.ndim != 2:
        raise ValueError("logits must be a 2-D array")
    if mask is not None:
        valid = np.asarray(mask, dtype=bool)
        if valid.shape != values.shape:
            raise ValueError("mask shape must match logits")
        if np.any(~valid.any(axis=1)):
            raise ValueError("every row must contain at least one valid action")
        values = np.where(valid, values, -np.inf)
    max_values = np.max(values, axis=1, keepdims=True)
    exp_values = np.exp(values - max_values)
    probs = exp_values / exp_values.sum(axis=1, keepdims=True)
    cdf = np.cumsum(probs, axis=1)
    u = uniform01(ctx, subject_ids, draw_index)
    action = (cdf < u[:, None]).sum(axis=1).astype(np.int16)
    selected = probs[np.arange(probs.shape[0]), action]
    entropy = -(probs * np.log(np.clip(probs, 1e-12, 1.0))).sum(axis=1)
    return action, selected.astype(np.float32), entropy.astype(np.float32)
