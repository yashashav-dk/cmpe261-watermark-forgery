import csv

import pytest

from wmforge.records import COLUMNS, RunLog

KEY = dict(stage="clean", scheme="TR", condition="", image_id="prompt0000", kind="watermarked", step=0)


def _rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def test_new_log_writes_header(tmp_path):
    path = tmp_path / "out" / "runs.csv"
    RunLog(path)
    assert _rows(path) == [COLUMNS]


def test_append_then_duplicate(tmp_path):
    log = RunLog(tmp_path / "runs.csv")
    assert log.append({**KEY, "raw_score": 12.5, "is_watermarked": 1}) is True
    assert log.append({**KEY, "raw_score": 99.0}) is False
    rows = _rows(tmp_path / "runs.csv")
    assert len(rows) == 2
    assert rows[1][COLUMNS.index("raw_score")] == "12.5"
    assert rows[1][COLUMNS.index("psnr")] == ""


def test_reopen_remembers_keys(tmp_path):
    path = tmp_path / "runs.csv"
    RunLog(path).append({**KEY})
    reopened = RunLog(path)
    assert reopened.has(**KEY)
    assert not reopened.has(**{**KEY, "step": 10})
    assert reopened.append({**KEY}) is False


def test_truncated_tail_is_dropped(tmp_path):
    path = tmp_path / "runs.csv"
    log = RunLog(path)
    log.append({**KEY})
    log.append({**KEY, "image_id": "prompt0001"})
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("clean,TR,,,prompt0002,waterm")
    reopened = RunLog(path)
    assert not reopened.has(**{**KEY, "image_id": "prompt0002"})
    assert reopened.append({**KEY, "image_id": "prompt0002"}) is True
    rows = _rows(path)
    assert len(rows) == 4
    assert all(len(row) == len(COLUMNS) for row in rows)


def test_unexpected_header_is_refused(tmp_path):
    path = tmp_path / "runs.csv"
    path.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected header"):
        RunLog(path)


def test_append_validates_columns(tmp_path):
    log = RunLog(tmp_path / "runs.csv")
    with pytest.raises(ValueError, match="unknown"):
        log.append({**KEY, "not_a_column": 1})
    with pytest.raises(ValueError, match="missing"):
        log.append({"stage": "clean"})
