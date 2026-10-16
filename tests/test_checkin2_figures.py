import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import checkin2_figures  # noqa: E402


@pytest.fixture(scope="module")
def frame():
    return checkin2_figures.load_all(ROOT)


def test_sources_cover_the_six_core_schemes(frame):
    assert set(frame.scheme) == set(checkin2_figures.ORDER)
    for scheme in checkin2_figures.ORDER:
        assert (frame[(frame.scheme == scheme) & (frame.stage == "real")].shape[0]) == 50
        assert (frame[(frame.scheme == scheme) & (frame.stage == "imprint") & (frame.kind == "forged")].image_id.nunique()) == 5


def test_stop_points_match_the_run_logs(frame):
    points = checkin2_figures.stop_points(frame)
    forged = points.groupby("scheme").forged.sum().to_dict()
    assert forged == {"GS": 5, "PRC": 5, "WIND": 5, "RI": 5, "SFW": 5, "TR": 4}
    assert points[points.scheme == "GS"].step.max() == 10
    missed = points[(points.scheme == "TR") & ~points.forged]
    assert missed.step.tolist() == [150]


def test_main_writes_three_figures(tmp_path):
    checkin2_figures.main(["--root", str(ROOT), "--out", str(tmp_path)])
    for name in ("fig1_baselines.png", "fig2_trajectories.png", "fig3_cost.png"):
        assert (tmp_path / name).stat().st_size > 10_000
