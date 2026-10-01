import pytest
from PIL import Image

from wmforge import report
from wmforge.records import RunLog

COVERS = ["101", "102", "103", "104", "105"]


def _row(stage, scheme, image_id, kind, step=0, condition="", **extra):
    return dict(stage=stage, scheme=scheme, condition=condition, image_id=image_id, kind=kind, step=step, **extra)


@pytest.fixture
def run_dir(tmp_path):
    log = RunLog(tmp_path / "runs.csv")
    for scheme in ("TR", "GS"):
        for index in range(50):
            log.append(_row("clean", scheme, f"prompt{index:04d}", "watermarked", raw_score=10.0, is_watermarked=1))
            log.append(_row("clean", scheme, f"prompt{index:04d}", "unwatermarked", raw_score=80.0, is_watermarked=0))
            log.append(_row("real", scheme, str(1000 + index), "real", raw_score=85.0, is_watermarked=0))
    images = tmp_path / "images"
    images.mkdir()
    for image_id in COVERS:
        log.append(_row("real", "TR", image_id, "real", raw_score=90.0, is_watermarked=0))
        common = dict(condition="C1", attack="imprint", psnr=25.0, ssim=0.8, lpips=0.1)
        log.append(_row("imprint", "TR", image_id, "forged", step=10, raw_score=70.0, is_watermarked=0, seconds=50.0, **common))
        log.append(_row("imprint", "TR", image_id, "forged", step=20, raw_score=40.0, is_watermarked=1, seconds=100.0, **common))
        log.append(_row("imprint", "TR", image_id, "done", condition="C1", attack="imprint", is_watermarked=1))
        Image.new("RGB", (32, 32), (10, 10, 10)).save(images / f"TR_{image_id}_cover.png")
        Image.new("RGB", (32, 32), (20, 10, 10)).save(images / f"TR_{image_id}_forged.png")
    return tmp_path


def test_summary_reports_rates_with_intervals(run_dir):
    summary = report.summary_markdown(report.load(run_dir / "runs.csv"))
    tr_line = next(line for line in summary.splitlines() if line.startswith("| TR "))
    assert "50/50 = 100% [93%, 100%]" in tr_line
    assert "0/50 = 0% [0%, 7%]" in tr_line
    assert "0/55 = 0% [0%, 7%]" in tr_line
    assert "5/5 = 100% [57%, 100%]" in tr_line
    assert "| 20 |" in tr_line
    assert "25.0 dB / 0.800 / 0.100" in tr_line
    assert "| 5.0 |" in tr_line


def test_summary_handles_scheme_without_imprint(run_dir):
    summary = report.summary_markdown(report.load(run_dir / "runs.csv"))
    gs_line = next(line for line in summary.splitlines() if line.startswith("| GS "))
    assert "50/50 = 100% [93%, 100%]" in gs_line
    assert gs_line.count("n/a") == 4


def test_summary_of_empty_log(tmp_path):
    RunLog(tmp_path / "runs.csv")
    assert report.summary_markdown(report.load(tmp_path / "runs.csv")) == "No rows in run log.\n"


def test_plot_and_grid_are_written(run_dir):
    df = report.load(run_dir / "runs.csv")
    assert report.plot_trajectories(df, run_dir / "trajectories.png") is True
    assert report.image_grid(df, run_dir / "images", run_dir / "grid.png") is True
    assert (run_dir / "trajectories.png").stat().st_size > 0
    assert (run_dir / "grid.png").stat().st_size > 0


def test_plot_and_grid_skip_when_no_forgery(tmp_path):
    log = RunLog(tmp_path / "runs.csv")
    log.append(_row("clean", "TR", "prompt0000", "watermarked", raw_score=10.0, is_watermarked=1))
    df = report.load(tmp_path / "runs.csv")
    assert report.plot_trajectories(df, tmp_path / "trajectories.png") is False
    assert report.image_grid(df, tmp_path / "images", tmp_path / "grid.png") is False
    assert not (tmp_path / "trajectories.png").exists()


def test_main_writes_all_outputs(run_dir, capsys):
    report.main(["--run", str(run_dir)])
    assert (run_dir / "summary.md").read_text(encoding="utf-8").startswith("| Scheme |")
    assert (run_dir / "trajectories.png").exists()
    assert (run_dir / "grid.png").exists()
    assert "| TR " in capsys.readouterr().out
