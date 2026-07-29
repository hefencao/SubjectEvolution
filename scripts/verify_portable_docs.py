from __future__ import annotations

import argparse
from pathlib import Path
import re

TEXT_SUFFIXES = {".md", ".txt", ".json", ".toml", ".yaml", ".yml"}
PATTERNS = (
    re.compile(r"/(?:mnt|home|tmp|opt)/[A-Za-z0-9_.\-/]+"),
    re.compile(r"[A-Za-z]:\\(?:[^\r\n\"]+)") ,
    re.compile(r"\bCONDA_PREFIX\b"),
    re.compile(r"\bcurrent (?:host|machine)\b", re.IGNORECASE),
    re.compile(r"(?:当前主机|本机环境|本机没有|本机无)"),
)


def verify(root: Path) -> list[str]:
    violations: list[str] = []
    candidates = [root / "README.md", root / "docs"]
    for candidate in candidates:
        paths = [candidate] if candidate.is_file() else sorted(candidate.rglob("*"))
        for path in paths:
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for pattern in PATTERNS:
                match = pattern.search(text)
                if match:
                    rel = path.relative_to(root)
                    line = text.count("\n", 0, match.start()) + 1
                    violations.append(f"{rel}:{line}: {match.group(0)}")
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify persistent documentation is portable.")
    parser.add_argument("--project", default=".")
    args = parser.parse_args(argv)
    root = Path(args.project).resolve()
    violations = verify(root)
    if violations:
        raise SystemExit("non-portable persistent documentation:\n" + "\n".join(violations))
    print("portable documentation verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
