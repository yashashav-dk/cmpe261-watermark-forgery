import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
RUN = ROOT / "results" / "checkin3" / "full"


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cell(**extra):
    base = dict(
        scheme="GS", stage="baseline", kind="watermarked", attack="", step=0, expected_n=100, observed_n=100,
        complete=True, native_successes=100, native_wilson95=[0.96, 1.0],
        calibrated_successes=100, calibrated_wilson95=[0.96, 1.0],
    )
    return dict(base, **extra)


def test_appendix_has_one_row_per_cell_with_both_rules():
    pytest.importorskip("markdown")
    pdf = load("checkin3_pdf")
    quality = {m: dict(mean=0.5, bootstrap95=[0.4, 0.6], n_finite=10) for m in ["psnr", "ssim", "lpips"]}
    table = [cell(), cell(stage="imprint", kind="forged", attack="imprint", step=150, observed_n=10, **quality),
             cell(stage="removal", attack="crop", native_successes=0, native_wilson95=[0.0, 0.037])]
    html = pdf.appendix_html(table)
    assert html.count("<tr><td>") == 3
    assert "F2 forgery, step 150" in html and "F3 removal, crop" in html
    assert "0/100 [0%, 4%]" in html and "PSNR 0.5" in html
    assert "3 of 3 required cells are complete" in html


def test_markdown_tables_and_relative_figures_survive_conversion(tmp_path):
    pytest.importorskip("markdown")
    pdf = load("checkin3_pdf")
    source = tmp_path / "report.md"
    source.write_text('# T\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n<figure>\n<img src="../fig.png">\n</figure>\n')
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps([cell()]))
    html = pdf.build_html(source, summary)
    assert "<table>" in html and '<img src="../fig.png">' in html
    assert f'<base href="{tmp_path.as_uri()}/">' in html


@pytest.mark.skipif(not (RUN / "measurements-v2.json").exists(), reason="committed Check-in 3 results not present")
def test_figures_draw_from_the_committed_log(tmp_path):
    figures = load("checkin3_figures")
    figures.main(["--run", str(RUN), "--out", str(tmp_path)])
    assert sorted(p.name for p in tmp_path.glob("*.png")) == [
        "fig1_baselines.png", "fig2_trajectories.png", "fig3_cost.png", "fig5_removal.png", "fig7_pipeline.png",
    ]
