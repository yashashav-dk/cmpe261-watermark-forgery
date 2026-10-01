"""Append-only CSV run log that survives interrupted runs."""
from __future__ import annotations

import csv
import os
from pathlib import Path

COLUMNS = [
    "stage",
    "scheme",
    "attack",
    "condition",
    "image_id",
    "kind",
    "step",
    "raw_score",
    "score",
    "is_watermarked",
    "psnr",
    "ssim",
    "lpips",
    "loss",
    "seconds",
    "seed",
    "target_rev",
    "attacker_rev",
]
KEY_COLUMNS = ("stage", "scheme", "condition", "image_id", "kind", "step")


class RunLog:
    """One row per measurement. A row whose key already exists is never written twice."""

    def __init__(self, path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._rows: dict[tuple[str, ...], dict[str, str]] = {}
        if self.path.exists() and self.path.stat().st_size > 0:
            self._load()
        else:
            self._write_all([])

    @staticmethod
    def _key(row: dict) -> tuple[str, ...]:
        return tuple(str(row[column]) for column in KEY_COLUMNS)

    def _write_all(self, rows: list[list[str]]) -> None:
        partial = self.path.with_suffix(self.path.suffix + ".part")
        with partial.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(COLUMNS)
            writer.writerows(rows)
        partial.replace(self.path)

    def _load(self) -> None:
        text = self.path.read_text(encoding="utf-8")
        lines = text.splitlines()
        # A line without its newline was cut off mid-write by an interrupted run.
        complete = lines if text.endswith("\n") else lines[:-1]
        parsed = list(csv.reader(complete))
        if not parsed or parsed[0] != COLUMNS:
            raise ValueError(f"{self.path} has an unexpected header; refusing to append to it")
        good = [row for row in parsed[1:] if len(row) == len(COLUMNS)]
        if len(complete) != len(lines) or len(good) != len(parsed) - 1:
            self._write_all(good)
        for row in good:
            stored = dict(zip(COLUMNS, row))
            self._rows[self._key(stored)] = stored

    def has(self, **key) -> bool:
        return self._key(key) in self._rows

    def get(self, **key) -> dict[str, str] | None:
        """The stored row for a key, with every value as the string written to the file."""
        stored = self._rows.get(self._key(key))
        return None if stored is None else dict(stored)

    def append(self, row: dict) -> bool:
        unknown = sorted(set(row) - set(COLUMNS))
        if unknown:
            raise ValueError(f"unknown columns: {unknown}")
        missing = [column for column in KEY_COLUMNS if column not in row]
        if missing:
            raise ValueError(f"missing key columns: {missing}")
        key = self._key(row)
        if key in self._rows:
            return False
        values = ["" if row.get(column) is None else row.get(column, "") for column in COLUMNS]
        with self.path.open("a", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(values)
            handle.flush()
            os.fsync(handle.fileno())
        self._rows[key] = {column: str(value) for column, value in zip(COLUMNS, values)}
        return True
