"""CuPy parity checks for the stateless random-key API.

The reference suite must remain runnable on CPU-only installations, so this
module is skipped unless both CuPy and a usable CUDA device are available.
"""

from __future__ import annotations

import numpy as np
import pytest

cp = pytest.importorskip("cupy", reason="CuPy is an optional GPU dependency")

try:
    if cp.cuda.runtime.getDeviceCount() < 1:
        pytest.skip("no CUDA device is available", allow_module_level=True)
    # Allocate once so a broken CUDA runtime is reported as a skip instead of
    # making an otherwise CPU-only test run fail during collection.
    cp.empty(1, dtype=cp.uint8)
except Exception:
    pytest.skip("CuPy has no usable CUDA runtime", allow_module_level=True)

from subject_evolution.random_api import (  # noqa: E402
    RandomContext,
    Stream,
    bernoulli,
    categorical_from_logits,
    keys,
    normal,
    uniform01,
)


def _context() -> RandomContext:
    return RandomContext(0x1234_5678_9ABC_DEF0, 71, 3, Stream.POLICY_ACTION)


def test_gpu_keys_and_uniform_match_cpu_bit_for_bit():
    ids = np.asarray([0, 1, 17, (1 << 32) + 13, (1 << 63) + 5, (1 << 64) - 1], dtype=np.uint64)
    ctx = _context()

    gpu_keys = keys(ctx, cp.asarray(ids), draw_index=19)
    gpu_uniform = uniform01(ctx, cp.asarray(ids), draw_index=19)

    assert isinstance(gpu_keys, cp.ndarray)
    assert isinstance(gpu_uniform, cp.ndarray)
    np.testing.assert_array_equal(cp.asnumpy(gpu_keys), keys(ctx, ids, draw_index=19))
    np.testing.assert_array_equal(cp.asnumpy(gpu_uniform), uniform01(ctx, ids, draw_index=19))


def test_gpu_distributions_follow_cpu_key_stream():
    ids = np.arange(1, 1025, dtype=np.uint64)
    gpu_ids = cp.asarray(ids)
    ctx = _context()
    probabilities = np.linspace(0.01, 0.99, ids.size, dtype=np.float64)

    cpu_bernoulli = bernoulli(ctx, ids, probabilities, draw_index=7)
    gpu_bernoulli = bernoulli(ctx, gpu_ids, cp.asarray(probabilities), draw_index=7)
    np.testing.assert_array_equal(cp.asnumpy(gpu_bernoulli), cpu_bernoulli)

    cpu_normal = normal(ctx, ids, mean=-0.25, stddev=1.75, draw_index=11)
    gpu_normal = normal(ctx, gpu_ids, mean=-0.25, stddev=1.75, draw_index=11)
    np.testing.assert_allclose(cp.asnumpy(gpu_normal), cpu_normal, rtol=1e-12, atol=1e-12)

    logits = np.column_stack(
        (
            np.full(ids.size, -0.5),
            np.linspace(-0.2, 0.7, ids.size),
            np.linspace(0.9, -0.4, ids.size),
            np.full(ids.size, 0.15),
        )
    )
    mask = np.ones_like(logits, dtype=bool)
    mask[::5, 1] = False
    mask[::7, 2] = False
    cpu_action, cpu_probability, cpu_entropy = categorical_from_logits(ctx, ids, logits, 0.7, mask, 23)
    gpu_action, gpu_probability, gpu_entropy = categorical_from_logits(
        ctx, gpu_ids, cp.asarray(logits), 0.7, cp.asarray(mask), 23
    )
    np.testing.assert_array_equal(cp.asnumpy(gpu_action), cpu_action)
    np.testing.assert_allclose(cp.asnumpy(gpu_probability), cpu_probability, rtol=1e-6, atol=1e-7)
    np.testing.assert_allclose(cp.asnumpy(gpu_entropy), cpu_entropy, rtol=1e-6, atol=1e-7)


def test_gpu_distribution_moments_match_cpu_reference():
    ids = np.arange(100_000, 165_536, dtype=np.uint64)
    gpu_ids = cp.asarray(ids)
    ctx = RandomContext(41, 12, 0, Stream.MEMORY_NOISE)

    cpu_uniform = uniform01(ctx, ids, draw_index=5)
    gpu_uniform = cp.asnumpy(uniform01(ctx, gpu_ids, draw_index=5))
    np.testing.assert_array_equal(gpu_uniform, cpu_uniform)
    assert abs(float(gpu_uniform.mean()) - 0.5) < 0.01
    assert abs(float(gpu_uniform.var()) - (1.0 / 12.0)) < 0.005

    cpu_normal = normal(ctx, ids, mean=0.0, stddev=1.0, draw_index=9)
    gpu_normal = cp.asnumpy(normal(ctx, gpu_ids, mean=0.0, stddev=1.0, draw_index=9))
    np.testing.assert_allclose(gpu_normal, cpu_normal, rtol=1e-12, atol=1e-12)
    assert abs(float(gpu_normal.mean())) < 0.02
    assert abs(float(gpu_normal.var()) - 1.0) < 0.03

