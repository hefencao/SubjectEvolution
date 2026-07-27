from __future__ import annotations

import pytest

from se.experiments.d2_module_audit import BRANCH_INTERVENTIONS, module_audit_effects


def test_module_audit_effects_include_nonadditivity() -> None:
    branches = {
        name: {"world.alive": value}
        for name, value in {
            "baseline": 100.0,
            "all-modules-neutral": 80.0,
            "module-0-neutral": 94.0,
            "module-1-neutral": 97.0,
            "module-2-neutral": 99.0,
            "module-3-neutral": 100.0,
        }.items()
    }
    assert set(branches) == set(BRANCH_INTERVENTIONS)
    effects = module_audit_effects(branches)
    assert effects["all_module_expression_effect"]["world.alive"] == 20.0
    assert effects["module_0_expression_effect"]["world.alive"] == 6.0
    assert effects["module_3_expression_effect"]["world.alive"] == 0.0
    assert effects["module_nonadditivity"]["world.alive"] == pytest.approx(10.0)
