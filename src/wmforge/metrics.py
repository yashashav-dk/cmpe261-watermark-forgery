"""Rates, intervals, and perceptual metrics."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image

Z95 = 1.959963984540054


def wilson_interval(successes: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0 <= successes <= n:
        raise ValueError("successes must be between 0 and n")
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    # The bounds are exactly 0 and 1 at the extremes; rounding would otherwise leave them a hair off.
    low = 0.0 if successes == 0 else max(0.0, centre - half)
    high = 1.0 if successes == n else min(1.0, centre + half)
    return low, high


def bootstrap_ci(values, n_resamples: int = 10_000, seed: int = 0, level: float = 0.95) -> tuple[float, float]:
    """Percentile bootstrap interval for the mean, resampling over items."""
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        raise ValueError("values must be non-empty")
    if np.isnan(arr).any():
        raise ValueError("values contain NaN")
    rng = np.random.default_rng(seed)
    index = rng.integers(0, arr.size, size=(n_resamples, arr.size))
    means = arr[index].mean(axis=1)
    tail = (1 - level) / 2
    low, high = np.quantile(means, [tail, 1 - tail])
    return float(low), float(high)


def _rgb_pair(a: Image.Image, b: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    if a.size != b.size:
        raise ValueError(f"image sizes differ: {a.size} vs {b.size}")
    return np.asarray(a.convert("RGB")), np.asarray(b.convert("RGB"))


def psnr(a: Image.Image, b: Image.Image) -> float:
    x, y = _rgb_pair(a, b)
    mse = float(np.mean((x.astype(np.float64) - y.astype(np.float64)) ** 2))
    if mse == 0:
        return float("inf")
    return 10 * math.log10(255.0**2 / mse)


def ssim(a: Image.Image, b: Image.Image) -> float:
    from skimage.metrics import structural_similarity

    x, y = _rgb_pair(a, b)
    return float(structural_similarity(x, y, channel_axis=2, data_range=255))


_LPIPS_MODEL = None


def lpips_distance(a: Image.Image, b: Image.Image, device: str = "cpu") -> float:
    import lpips
    import torch

    global _LPIPS_MODEL
    if _LPIPS_MODEL is None:
        _LPIPS_MODEL = lpips.LPIPS(net="alex", verbose=False).eval()
    model = _LPIPS_MODEL.to(device)
    x, y = _rgb_pair(a, b)

    def to_tensor(arr: np.ndarray):
        scaled = arr.astype(np.float32) / 127.5 - 1.0
        return torch.from_numpy(scaled).permute(2, 0, 1).unsqueeze(0).to(device)

    with torch.no_grad():
        return float(model(to_tensor(x), to_tensor(y)).item())
