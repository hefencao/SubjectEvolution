"""Optional environment-process implementations shipped outside the core loop."""

from __future__ import annotations

_BUILTINS_REGISTERED = False


def register_builtin_environment_processes() -> None:
    global _BUILTINS_REGISTERED
    if _BUILTINS_REGISTERED:
        return
    from .moving_gaussian_hazard import register_plugin

    register_plugin()
    _BUILTINS_REGISTERED = True


__all__ = ["register_builtin_environment_processes"]
