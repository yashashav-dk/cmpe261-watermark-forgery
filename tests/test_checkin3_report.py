from wmforge.checkin3_report import summarize


def test_partial_denominators_and_exact_budgets_are_explicit():
    rows = []
    for step, verdict in [(10, True), (50, False), (100, True), (150, False)]:
        rows.append(
            dict(
                scheme="PRC",
                stage="imprint",
                kind="forged",
                attack="imprint",
                step=step,
                image_id="1",
                native=verdict,
                score=1 if verdict else 0,
                psnr=25.0,
                ssim=0.9,
                lpips=0.1,
            )
        )
    table = summarize(rows, {"PRC": {"included": True, "threshold": 0.5}})
    cells = [c for c in table if c["stage"] == "imprint" and c["scheme"] == "PRC"]
    assert [
        (c["step"], c["native_successes"], c["expected_n"], c["observed_n"])
        for c in cells
    ] == [(50, 0, 10, 1), (100, 1, 10, 1), (150, 0, 10, 1)]
    assert all(not c["complete"] for c in cells)
    assert all(c["calibrated_label"] == "PRC score-only calibrated test" for c in cells)


def test_absent_calibration_cannot_hide_attack_requirements():
    table = summarize([], {})
    assert len(table) == 60
    assert sum(c["stage"] == "imprint" for c in table) == 18
    assert sum(c["stage"] == "removal" for c in table) == 24
    assert not any(c["complete"] for c in table)


def test_report_rejects_calibration_without_its_full_baseline(tmp_path):
    import json
    import pytest
    from wmforge.checkin3_report import report

    (tmp_path / "TR-calibration.json").write_text(
        json.dumps({"included": False, "threshold": 0})
    )
    with pytest.raises(ValueError, match="incomplete"):
        report(tmp_path)
