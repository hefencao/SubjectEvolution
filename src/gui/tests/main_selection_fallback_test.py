from pathlib import Path
text=(Path(__file__).resolve().parents[1]/'src/gui/src/main.cpp').read_text()
assert 'The individual died or left the frame.' in text
assert 'options.selected_entity_id = 0;' in text
assert 'renderer.group_behavior(options.selected_group_id, options.overlay_temporal) == nullptr' in text
print('selection fallback source check: ok')
