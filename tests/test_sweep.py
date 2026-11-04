from PIL import Image

import pytest

from wmforge.sweep import (
    CROP_RATIOS,
    PURIFICATION_STRENGTHS,
    apply_strength,
    crop_at_ratio,
    jpeg_at_quality,
    summarize_sweep,
    sweep_key,
)


def test_crop_ratio_grid_and_size_preserved():
    image = Image.new("RGB", (512, 512), (10, 20, 30))
    assert CROP_RATIOS[0] == 0.95 and CROP_RATIOS[-1] == 0.60
    for ratio in CROP_RATIOS:
        out = crop_at_ratio(image, ratio)
        assert out.size == (512, 512)
    with pytest.raises(ValueError):
        crop_at_ratio(image, 0.0)
    with pytest.raises(ValueError):
        crop_at_ratio(image, 1.5)


def test_jpeg_and_blur_parameter_checks():
    image = Image.new("RGB", (64, 64), (200, 100, 50))
    assert jpeg_at_quality(image, 95).size == (64, 64)
    assert apply_strength(image, "blur", 0).size == (64, 64)
    with pytest.raises(ValueError):
        jpeg_at_quality(image, 100)
    with pytest.raises(ValueError):
        apply_strength(image, "purification", 0.3, purifier=None)


def test_sweep_key_and_summary_counts():
    assert PURIFICATION_STRENGTHS == (0.10, 0.20, 0.30, 0.40, 0.50)
    key = sweep_key("TR", "crop", 0.8, "prompt0000")
    assert key["attack"] == "crop@0.8"
    assert key["stage"] == "removal_sweep"
    rows = [
        dict(scheme="TR", stage="removal_sweep", attack="crop@0.8", native=True, score=-40.0),
        dict(scheme="TR", stage="removal_sweep", attack="crop@0.8", native=False, score=-55.0),
        dict(scheme="TR", stage="removal_sweep", attack="crop@0.7", native=False, score=-60.0),
    ]
    summary = summarize_sweep(rows, "crop", [0.8, 0.7], "TR", threshold=-50.0)
    assert summary[0]["native_successes"] == 1
    assert summary[0]["calibrated_successes"] == 1
    assert summary[1]["observed_n"] == 1
