

def test_thin_checkpoint_flag_is_explicit_runtime_storage_policy() -> None:
    from se.cmd.multi_seed import build_parser

    args = build_parser().parse_args([
        "--config", "config.json",
        "--seeds", "1",
        "--output", "runs",
        "--thin-checkpoints-only",
    ])
    assert args.thin_checkpoints_only is True


def test_checkpoint_storage_controls_are_explicit() -> None:
    from se.cmd.multi_seed import build_parser

    parser = build_parser()
    no_checkpoints = parser.parse_args([
        "--config", "config.json", "--seeds", "1", "--output", "runs",
        "--no-checkpoints",
    ])
    assert no_checkpoints.no_checkpoints is True
    exact_only = parser.parse_args([
        "--config", "config.json", "--seeds", "1", "--output", "runs",
        "--checkpoint-ticks", "10,20", "--disable-periodic-checkpoints",
    ])
    assert exact_only.disable_periodic_checkpoints is True
