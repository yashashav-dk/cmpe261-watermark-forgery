"""Strength sweeps for crop-and-rescale and diffusion purification.

Check-in 3 measured each removal attack at one toolkit default. The two attacks
that split native and calibrated decisions (crop, purification) are re-run here
at a fixed grid of strengths so the report can show where each rule fails.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Iterable, Optional

from PIL import Image, ImageFilter

from wmforge import benchmark as b

# Inclusive grids used for Check-in 4. Crop ratio is the kept side length.
CROP_RATIOS = (0.95, 0.90, 0.85, 0.80, 0.70, 0.60)
PURIFICATION_STRENGTHS = (0.10, 0.20, 0.30, 0.40, 0.50)


def crop_at_ratio(image: Image.Image, ratio: float) -> Image.Image:
    if not 0.0 < ratio <= 1.0:
        raise ValueError(f"crop ratio must be in (0, 1], got {ratio}")
    width, height = image.size
    side_w, side_h = int(width * ratio), int(height * ratio)
    if side_w < 1 or side_h < 1:
        raise ValueError(f"crop ratio {ratio} leaves an empty crop")
    left, top = (width - side_w) // 2, (height - side_h) // 2
    return image.crop((left, top, left + side_w, top + side_h)).resize(image.size)


def jpeg_at_quality(image: Image.Image, quality: int) -> Image.Image:
    if not 1 <= quality <= 95:
        raise ValueError(f"JPEG quality must be in [1, 95], got {quality}")
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def blur_at_radius(image: Image.Image, radius: float) -> Image.Image:
    if radius < 0:
        raise ValueError(f"blur radius must be non-negative, got {radius}")
    if radius == 0:
        return image.copy()
    return image.filter(ImageFilter.GaussianBlur(radius=radius))


def apply_strength(image: Image.Image, attack: str, strength: float, purifier=None, seed: int = 0):
    """Apply one parameterized attack. Purification needs a MarkDiffusion editor."""
    if attack == "crop":
        return crop_at_ratio(image, strength)
    if attack == "jpeg":
        return jpeg_at_quality(image, int(strength))
    if attack == "blur":
        return blur_at_radius(image, strength)
    if attack == "purification":
        if purifier is None:
            raise ValueError("purification requires a purifier")
        from wmforge.checkin3 import seed_all

        seed_all(seed)
        # MarkDiffusion DiffusionPurification takes strength at construction; callers
        # pass a factory that rebuilds the editor for each strength.
        return purifier.edit(image, prompt="")
    raise ValueError(f"unsupported sweep attack {attack!r}")


def sweep_key(scheme: str, attack: str, strength: float, image_id: str) -> dict:
    label = f"{attack}@{strength:g}"
    return dict(
        protocol="checkin4-sweep-v1",
        scheme=scheme,
        stage="removal_sweep",
        attack=label,
        image_id=image_id,
        kind="watermarked",
        step=0,
    )


def run_crop_sweep(harness, log, root, ratios: Iterable[float] = CROP_RATIOS):
    """Re-detect the Check-in 3 watermarked images after crops at each ratio."""
    sources = [
        r
        for r in log.rows
        if r["scheme"] == harness.scheme
        and r["stage"] == "baseline"
        and r["kind"] == "watermarked"
    ]
    if not sources:
        raise ValueError(f"no watermarked baselines for {harness.scheme}")
    for ratio in ratios:
        for source in sources:
            key = sweep_key(harness.scheme, "crop", ratio, source["image_id"])
            old = log.get(**key) if hasattr(log, "get") else None
            if old:
                b.verify_artifact(root, old)
                continue
            b.verify_artifact(root, source)
            with Image.open(Path(root) / source["artifact"]) as image:
                transformed = crop_at_ratio(image.convert("RGB"), ratio)
            relative = (
                f"images/{harness.scheme}/sweep/crop_{ratio:g}_{source['image_id']}.png"
            )
            log.append(
                b.measurement(
                    harness,
                    transformed,
                    key,
                    root,
                    relative,
                    seed=source["seed"],
                    source_sha256=source["sha256"],
                )
            )


def summarize_sweep(rows, attack_prefix: str, strengths: Iterable[float], scheme: str, threshold: Optional[float]):
    """Count native and calibrated detections per strength for one scheme."""
    out = []
    for strength in strengths:
        label = f"{attack_prefix}@{strength:g}"
        subset = [
            r
            for r in rows
            if r["scheme"] == scheme
            and r["stage"] == "removal_sweep"
            and r["attack"] == label
        ]
        n = len(subset)
        native = sum(1 for r in subset if r["native"])
        if threshold is None:
            calibrated = None
        else:
            calibrated = sum(1 for r in subset if r["score"] > threshold)
        out.append(
            dict(
                scheme=scheme,
                attack=attack_prefix,
                strength=strength,
                observed_n=n,
                native_successes=native,
                calibrated_successes=calibrated,
            )
        )
    return out
