"""Generation and detection through MarkDiffusion."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional

from PIL import Image

IMAGE_SIZE = 512
NUM_INFERENCE_STEPS = 50
GUIDANCE_SCALE = 7.5


@dataclass(frozen=True)
class SchemeInfo:
    score_key: str
    higher_is_watermarked: bool


# Score keys and directions read from MarkDiffusion's detectors at the pinned commit.
# PRC's score direction is unverified; only its verdict is relied on.
SCHEMES = {
    "TR": SchemeInfo("l1_distance", False),
    "RI": SchemeInfo("l1_distance", False),
    "SFW": SchemeInfo("l1_distance", False),
    "GS": SchemeInfo("bit_acc", True),
    "WIND": SchemeInfo("cosine_similarity", True),
    "PRC": SchemeInfo("score", True),
}


@dataclass(frozen=True)
class Detection:
    raw_score: float
    score: float
    is_watermarked: bool


def parse_detection(scheme: str, result: dict) -> Detection:
    """Turn a MarkDiffusion detection dict into a Detection; higher score means more watermarked."""
    if scheme not in SCHEMES:
        raise ValueError(f"unknown scheme {scheme!r}; known schemes: {sorted(SCHEMES)}")
    info = SCHEMES[scheme]
    if info.score_key not in result or "is_watermarked" not in result:
        raise ValueError(
            f"{scheme} detector result lacks {info.score_key!r} or 'is_watermarked': keys {sorted(result)}"
        )
    raw = float(result[info.score_key])
    if not math.isfinite(raw):
        raise ValueError(f"{scheme} detector score is not finite: {raw}")
    return Detection(raw, raw if info.higher_is_watermarked else -raw, bool(result["is_watermarked"]))


class Harness:
    """One watermarking scheme on one target pipeline."""

    def __init__(
        self,
        scheme: str,
        watermark,
        latent_sampler: Callable[[int], object],
        detect_guidance_scale: Optional[float] = None,
    ) -> None:
        if scheme not in SCHEMES:
            raise ValueError(f"unknown scheme {scheme!r}; known schemes: {sorted(SCHEMES)}")
        self.scheme = scheme
        self.watermark = watermark
        self._latent_sampler = latent_sampler
        self._detect_guidance_scale = detect_guidance_scale

    def generate(self, prompt: str, seed: int, watermarked: bool) -> Image.Image:
        # MarkDiffusion fixes these at construction; reset them so each image starts from its own noise.
        self.watermark.config.gen_seed = seed
        self.watermark.config.init_latents = self._latent_sampler(seed)
        if watermarked:
            return self.watermark.generate_watermarked_media(prompt)
        return self.watermark.generate_unwatermarked_media(prompt)

    def detect(self, image: Image.Image) -> Detection:
        kwargs = {}
        if self._detect_guidance_scale is not None:
            kwargs["guidance_scale"] = self._detect_guidance_scale
        return parse_detection(self.scheme, self.watermark.detect_watermark_in_media(image, **kwargs))


def load_target_pipe(model_id: str, revision: str, device: str):
    import torch
    from diffusers import DPMSolverMultistepScheduler, StableDiffusionPipeline

    scheduler = DPMSolverMultistepScheduler.from_pretrained(model_id, subfolder="scheduler", revision=revision)
    # Full precision on every device: MarkDiffusion's Gaussian Shading builds float32 latents,
    # which a half-precision pipeline rejects.
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id, revision=revision, scheduler=scheduler, torch_dtype=torch.float32, safety_checker=None
    ).to(device)
    pipe.set_progress_bar_config(disable=True)
    return pipe


def build_harness(scheme: str, pipe, device: str) -> Harness:
    import torch
    from markdiffusion.utils import DiffusionConfig
    from markdiffusion.utils.media_utils import get_random_latents
    from markdiffusion.watermark import AutoWatermark

    config = DiffusionConfig(
        scheduler=pipe.scheduler,
        pipe=pipe,
        device=device,
        image_size=(IMAGE_SIZE, IMAGE_SIZE),
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        gen_seed=0,
        inversion_type="ddim",
        dtype=pipe.unet.dtype,
    )
    watermark = AutoWatermark.load(scheme, diffusion_config=config)

    def sample_latents(seed: int):
        generator = torch.Generator(device=device).manual_seed(seed)
        return get_random_latents(pipe, height=IMAGE_SIZE, width=IMAGE_SIZE, generator=generator)

    return Harness(scheme, watermark, sample_latents)
