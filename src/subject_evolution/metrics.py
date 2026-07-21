from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
import numpy as np


class MetricsWriter:
    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.output_dir / "metrics.csv"
        self._file = self.csv_path.open("w", newline="", encoding="utf-8")
        self._writer: csv.DictWriter[str] | None = None
        self.rows: list[dict[str, Any]] = []

    def write(self, row: dict[str, Any]) -> None:
        clean = {key: (value.item() if isinstance(value, np.generic) else value) for key, value in row.items()}
        if self._writer is None:
            self._writer = csv.DictWriter(self._file, fieldnames=list(clean.keys()))
            self._writer.writeheader()
        self._writer.writerow(clean)
        self._file.flush()
        self.rows.append(clean)

    def close(self) -> None:
        self._file.close()
        summary = self.rows[-1] if self.rows else {}
        (self.output_dir / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
