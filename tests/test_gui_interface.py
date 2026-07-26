from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest

from se.cfg import load_config
from se.gui import (
    RealtimePublisherAttachment,
    SharedFramePublisher,
    SharedFrameReader,
)
from se.gui.runner import run
from se.runtime.sim import Simulation


ROOT = Path(__file__).resolve().parents[1]


def _config(*, ticks: int = 3):
    base = load_config(ROOT / "configs" / "mvp_short_k1_compat.json")
    return replace(
        base,
        run=replace(
            base.run,
            ticks=ticks,
            metrics_period=1,
            checkpoint_period=max(ticks, 1),
            evolution_evaluation_period=max(ticks, 1),
            validation_mode=True,
        ),
        world=replace(
            base.world,
            width=32.0,
            height=32.0,
            grid_x=8,
            grid_y=8,
            initial_entities=16,
            max_entities=24,
        ),
    )


def test_shared_frame_round_trip_and_detach(tmp_path: Path) -> None:
    simulation = Simulation(_config(), tmp_path / "run", backend="cpu")
    stream = tmp_path / "eco_live.bin"
    manifest = tmp_path / "eco_live.protocol.json"
    publisher = SharedFramePublisher.from_simulation(
        simulation,
        path=stream,
        every_ticks=1,
        manifest_path=manifest,
    )
    attachment = RealtimePublisherAttachment(simulation, publisher)
    try:
        with SharedFrameReader(stream) as reader:
            initial = reader.read_latest()
            assert initial.tick == 0
            assert initial.entities.size == int(np.count_nonzero(simulation.entities.alive))
            assert np.array_equal(
                np.sort(initial.entities["entity_id"]),
                np.sort(simulation.entities.entity_id[simulation.entities.alive]),
            )

            simulation.step()
            frame = reader.read_latest()
            assert frame.tick == 1
            assert np.array_equal(frame.resources, simulation.environment.resources)
            assert np.array_equal(frame.hazard, simulation.environment.hazard)

        sequence = publisher.sequence
        attachment.detach()
        simulation.step()
        assert publisher.sequence == sequence
    finally:
        attachment.close()

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["state"] == "closed"
    assert payload["protocol_version"] == 1
    assert payload["layout"]["entity_record_bytes"] == 72
    assert payload["publication_semantics"]["scientific_feedback"] is False


def test_duplicate_attachment_is_rejected(tmp_path: Path) -> None:
    simulation = Simulation(_config(), tmp_path / "run", backend="cpu")
    first = SharedFramePublisher.from_simulation(
        simulation, path=tmp_path / "first.bin", every_ticks=1
    )
    second = SharedFramePublisher.from_simulation(
        simulation, path=tmp_path / "second.bin", every_ticks=1
    )
    attachment = RealtimePublisherAttachment(simulation, first)
    try:
        with pytest.raises(RuntimeError, match="already attached"):
            RealtimePublisherAttachment(simulation, second)
    finally:
        attachment.close()
        second.close()


def test_gui_runner_writes_resolved_config_and_final_frame(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    cfg = _config(ticks=2)
    from dataclasses import asdict

    config_path.write_text(json.dumps(asdict(cfg)), encoding="utf-8")
    output = tmp_path / "output"
    stream = tmp_path / "gui.bin"
    result = run(
        config_path=config_path,
        output=output,
        stream=stream,
        backend="cpu",
        until_tick=2,
        publish_every=1,
    )
    assert int(result["tick"]) == 2
    assert (output / "resolved_config.json").is_file()
    with SharedFrameReader(stream) as reader:
        frame = reader.read_latest()
    assert frame.tick == 2
    manifest = json.loads((tmp_path / "gui.bin.json").read_text(encoding="utf-8"))
    assert manifest["state"] == "closed"
    assert manifest["last_tick"] == 2


def test_legacy_gui_interface_paths_resolve_to_canonical_types() -> None:
    from se.gui import (
        SharedFramePublisher as LegacyPublisher,
    )
    from se.gui import SharedFramePublisher as CanonicalPublisher

    assert LegacyPublisher is CanonicalPublisher
