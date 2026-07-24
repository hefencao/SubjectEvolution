from pathlib import Path

root = Path(__file__).resolve().parents[1]
src = root / 'src/gui/src'
facade = src / 'renderer.cpp'
modules = [
    src / 'renderer_internal.cpp',
    src / 'renderer_context.cpp',
    src / 'renderer_core.cpp',
    src / 'renderer_environment.cpp',
    src / 'renderer_observation.cpp',
    src / 'renderer_groups.cpp',
    src / 'renderer_draw.cpp',
    src / 'renderer_gpu.cpp',
]
assert len(facade.read_text().splitlines()) < 20
assert all(path.exists() for path in modules)
assert max(len(path.read_text().splitlines()) for path in modules) < 1400
assert (src / 'render/renderer_internal.hpp').exists()
assert (src / 'render/renderer_state.hpp').exists()
print('renderer translation-unit layout: ok')
