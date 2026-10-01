import math

import numpy as np
import pytest
from PIL import Image

from wmforge import metrics


def _solid(value, size=(32, 32)):
    return Image.new("RGB", size, (value, value, value))


def test_wilson_all_success():
    low, high = metrics.wilson_interval(10, 10)
    assert low == pytest.approx(0.7225, abs=1e-3)
    assert high == 1.0


def test_wilson_no_success():
    low, high = metrics.wilson_interval(0, 10)
    assert low == 0.0
    assert high == pytest.approx(0.2775, abs=1e-3)


def test_wilson_half():
    low, high = metrics.wilson_interval(5, 10)
    assert low == pytest.approx(0.2366, abs=1e-3)
    assert high == pytest.approx(0.7634, abs=1e-3)


@pytest.mark.parametrize("successes,n", [(1, 0), (-1, 10), (11, 10)])
def test_wilson_rejects_bad_counts(successes, n):
    with pytest.raises(ValueError):
        metrics.wilson_interval(successes, n)


def test_bootstrap_constant_values():
    assert metrics.bootstrap_ci([3.0] * 20) == (3.0, 3.0)


def test_bootstrap_is_deterministic_and_brackets_mean():
    values = np.random.default_rng(1).normal(5.0, 1.0, 200)
    first = metrics.bootstrap_ci(values, seed=7)
    second = metrics.bootstrap_ci(values, seed=7)
    assert first == second
    assert first[0] < values.mean() < first[1]


def test_bootstrap_rejects_empty_and_nan():
    with pytest.raises(ValueError):
        metrics.bootstrap_ci([])
    with pytest.raises(ValueError):
        metrics.bootstrap_ci([1.0, float("nan")])


def test_psnr_identical_is_infinite():
    assert math.isinf(metrics.psnr(_solid(10), _solid(10)))


def test_psnr_known_value():
    # mean squared error 16**2 = 256 -> 10*log10(255**2 / 256)
    assert metrics.psnr(_solid(0), _solid(16)) == pytest.approx(24.05, abs=0.01)


def test_psnr_rejects_size_mismatch():
    with pytest.raises(ValueError):
        metrics.psnr(_solid(0, (32, 32)), _solid(0, (16, 16)))


def test_ssim_identical_and_different():
    noise = Image.fromarray(np.random.default_rng(0).integers(0, 256, (32, 32, 3), dtype=np.uint8))
    assert metrics.ssim(noise, noise) == pytest.approx(1.0)
    assert metrics.ssim(noise, _solid(128)) < 0.5


def test_lpips_identical_is_zero():
    pytest.importorskip("lpips")
    noise = Image.fromarray(np.random.default_rng(0).integers(0, 256, (64, 64, 3), dtype=np.uint8))
    assert metrics.lpips_distance(noise, noise) == pytest.approx(0.0, abs=1e-6)
