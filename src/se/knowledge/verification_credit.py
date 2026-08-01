"""Evidence extraction for delayed value attribution of transferred knowledge."""

from __future__ import annotations

import numpy as np


def transferred_copy_verification_credit(
    *,
    outcome: np.ndarray,
    prior_mean: np.ndarray,
    outcome_scales: np.ndarray,
    prior_confidence: float,
    created_tick: int,
    verification_tick: int,
) -> tuple[float, float, int]:
    """Return signed prediction quality, evidence weight and realized delay.

    This records verifiable information quality only.  It is not a causal
    estimate of whether the holder used the copy or benefited downstream.
    """
    normalized_error = np.clip(
        np.abs(np.asarray(outcome, dtype=np.float64) - np.asarray(prior_mean, dtype=np.float64))
        / np.asarray(outcome_scales, dtype=np.float64),
        0.0,
        1.0,
    )
    signed_quality = float(np.clip(1.0 - 2.0 * normalized_error.mean(), -1.0, 1.0))
    evidence = float(max(prior_confidence, 0.05))
    delay = max(int(verification_tick) - int(created_tick), 0)
    return signed_quality, evidence, delay


__all__ = ["transferred_copy_verification_credit"]
