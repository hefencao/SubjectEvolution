import numpy as np

from subject_evolution.random_api import RandomContext, Stream, categorical_from_logits, keys, normal, uniform01


def test_uniform_is_reproducible_and_order_independent():
    ids = np.asarray([11, 22, 33, 44], dtype=np.uint64)
    ctx = RandomContext(123, 9, 2, Stream.POLICY_ACTION)
    a = uniform01(ctx, ids, 7)
    b = uniform01(ctx, ids, 7)
    assert np.array_equal(a, b)
    reversed_values = uniform01(ctx, ids[::-1], 7)[::-1]
    assert np.array_equal(a, reversed_values)


def test_categorical_respects_mask():
    ids = np.asarray([1, 2, 3], dtype=np.uint64)
    logits = np.zeros((3, 4), dtype=np.float32)
    mask = np.asarray([[False, True, False, False]] * 3)
    ctx = RandomContext(1, 0, 0, Stream.POLICY_ACTION)
    action, probability, entropy = categorical_from_logits(ctx, ids, logits, 1.0, mask)
    assert np.all(action == 1)
    assert np.allclose(probability, 1.0)
    assert np.allclose(entropy, 0.0)


def test_per_row_draw_indices_match_scalar_key_streams():
    ids = np.asarray([11, 22, 33, 44], dtype=np.uint64)
    draw_indices = np.asarray([0, 7, 123, (1 << 31) - 2], dtype=np.uint64)
    ctx = RandomContext(123, 9, 2, Stream.POLICY_ACTION)

    batched_keys = keys(ctx, ids, draw_indices)
    expected_keys = np.asarray(
        [keys(ctx, ids[row : row + 1], int(draw_indices[row]))[0] for row in range(ids.size)],
        dtype=np.uint64,
    )
    np.testing.assert_array_equal(batched_keys, expected_keys)

    batched_normal = normal(ctx, ids, mean=0.25, stddev=1.75, draw_index=draw_indices)
    expected_normal = np.asarray(
        [normal(ctx, ids[row : row + 1], 0.25, 1.75, int(draw_indices[row]))[0] for row in range(ids.size)]
    )
    np.testing.assert_array_equal(batched_normal, expected_normal)
