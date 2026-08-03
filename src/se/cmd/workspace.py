"""Inspect and configure project-local external workspace directories."""
from __future__ import annotations

import argparse
import json

from se.workspace import (
    configure_patch_dir,
    configure_result_bundle_dir,
    configured_path,
    find_project_root,
    load_workspace_settings,
)


def _print_settings(data: dict[str, object]) -> None:
    print(f"project root: {data['project_root']}")
    result = data["result_bundle_dir"] or "<not configured>"
    patch = data["patch_dir"] or "<not configured>"
    print(f"result bundle directory: {result}")
    print(f"patch directory: {patch}")
    print(f"settings file: {data['config_path']}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Inspect or configure project-external workspace directories."
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    show = subparsers.add_parser("show", help="show current workspace settings")
    show.add_argument("--json", action="store_true")

    config = subparsers.add_parser("config", help="set workspace directories")
    config.add_argument("--set-result-dir")
    config.add_argument("--set-patch-dir")
    config.add_argument("--json", action="store_true")

    path = subparsers.add_parser("path", help="print one configured directory only")
    path.add_argument("kind", choices=("result", "patch"))

    args = parser.parse_args(argv)
    try:
        root = find_project_root()
        if args.action == "path":
            print(configured_path(root, args.kind))
            return
        data = load_workspace_settings(root)
        if args.action == "config":
            if not args.set_result_dir and not args.set_patch_dir:
                parser.error("config requires --set-result-dir and/or --set-patch-dir")
            if args.set_result_dir:
                data = configure_result_bundle_dir(root, args.set_result_dir)
            if args.set_patch_dir:
                data = configure_patch_dir(root, args.set_patch_dir)
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        _print_settings(data)


if __name__ == "__main__":
    main()
