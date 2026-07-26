from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "src/gui/src/launcher.cpp").read_text(encoding="utf-8")

experiment = source.index('section("Experiment")')
file_name = source.index('text_field("save_name"', experiment)
new_action = source.index('ActionIcon::NewFile', file_name)
save_action = source.index('ActionIcon::SaveFile', new_action)
single_mode = source.index('filled_button(single_rect', save_action)
multi_mode = source.index('filled_button(multi_rect', single_mode)
cpu_backend = source.index('filled_button(cpu_rect', multi_mode)
basic = source.index('section("Basic overrides")', cpu_backend)
extended = source.index('"Extended overrides [-]"', basic)
recent = source.index('section("Recent experiments")', extended)
command = source.index('layout.command_preview', recent)
copy_action = source.index('ActionIcon::Copy', command)
close_action = source.index('ActionIcon::Close', copy_action)
run_action = source.index('ActionIcon::Run', close_action)

assert experiment < file_name < new_action < save_action
assert save_action < single_mode < multi_mode < cpu_backend < basic < extended < recent
assert recent < command < copy_action < close_action < run_action

for redundant in (
    'label("Mode")',
    'label("Backend")',
    "CPU: parity and reproducibility",
    "Streams one simulation into the runtime viewer.",
    "Runs the seed queue sequentially, never in parallel.",
):
    assert redundant not in source, redundant

print("launcher v24 information architecture: ok")
