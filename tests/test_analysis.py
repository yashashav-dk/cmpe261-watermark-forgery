import json
from pathlib import Path

from wmforge.analysis import (
    calibrated_accept,
    first_accept_step,
    forgery_table,
    forgeability_order,
    load_calibrations,
    load_rows,
    run_all,
    threshold_disagreement,
)


ROOT = Path("results/checkin3/full")


def test_load_and_calibrated_rule():
    rows = load_rows(ROOT / "measurements-v2.json")
    assert len(rows) == 5700
    cal = load_calibrations(ROOT)
    assert set(cal) == {"TR", "RI", "SFW", "GS", "WIND", "PRC"}
    row = next(r for r in rows if r["scheme"] == "GS" and r["stage"] == "baseline")
    assert isinstance(calibrated_accept(row, cal["GS"]), bool)


def test_first_accept_and_forgery_counts_match_checkin3():
    rows = load_rows(ROOT / "measurements-v2.json")
    cal = load_calibrations(ROOT)
    traj = [
        r
        for r in rows
        if r["scheme"] == "GS" and r["stage"] == "imprint" and r["image_id"] == "410878"
    ]
    assert first_accept_step(traj, "native") == 10
    table = forgery_table(rows, cal)
    gs150 = next(r for r in table if r["scheme"] == "GS" and r["budget"] == 150)
    assert gs150["native_successes"] == 10
    assert gs150["calibrated_successes"] == 10
    tr150 = next(r for r in table if r["scheme"] == "TR" and r["budget"] == 150)
    assert tr150["native_successes"] == 6
    order = forgeability_order(rows, cal)
    assert order[0]["scheme"] == "GS"
    assert order[0]["median_first_native"] == 10


def test_disagreement_and_run_all_roundtrip(tmp_path):
    rows = load_rows(ROOT / "measurements-v2.json")
    cal = load_calibrations(ROOT)
    disagree = threshold_disagreement(rows, cal)
    ri = next(r for r in disagree if r["scheme"] == "RI" and r["stage"] == "imprint")
    # Ring-ID calibrated accepts many forgeries the native rule rejects.
    assert ri["calibrated_only"] > 0
    analysis = run_all(ROOT / "measurements-v2.json", ROOT)
    path = tmp_path / "analysis.json"
    path.write_text(json.dumps(analysis))
    loaded = json.loads(path.read_text())
    assert "forgery" in loaded and "removal" in loaded
