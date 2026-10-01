# wmforge - forgery benchmark for semantic watermarks in diffusion models
# Copyright (C) 2026 Kanaka Sarat Siripurapu, Latha Boralingaiah, Yashashav Devalapalli Kamalraj
#
# This file is adapted from the imprint-forgery attack in
# https://github.com/and-mill/semantic-forgery (Copyright (C) 2025 Andreas Mueller),
# the official implementation of "Black-Box Forgery Attacks on Semantic Watermarks
# for Diffusion Models" (CVPR 2025), which is licensed under GPL-3.0.
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3, as published by the Free
# Software Foundation. It is distributed WITHOUT ANY WARRANTY; see LICENSE.
"""Imprint forgery: move a cover image's inverted latent onto a watermarked reference's."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import torch
from PIL import Image
from torch.utils.checkpoint import checkpoint


@dataclass
class Attacker:
    pipe: object
    inverse_scheduler: object
    num_inversion_steps: int = 50


@dataclass
class StepRecord:
    step: int
    loss: float
    seconds: float


@dataclass
class ImprintResult:
    image: Image.Image
    steps_run: int
    records: list[StepRecord]
    stopped_early: bool


def make_attacker(pipe, inverse_scheduler, num_inversion_steps: int = 50) -> Attacker:
    for module in (pipe.unet, pipe.vae, pipe.text_encoder):
        module.requires_grad_(False)
    return Attacker(pipe, inverse_scheduler, num_inversion_steps)


def load_attacker(
    model_id: str, revision: Optional[str] = None, device: str = "cuda", num_inversion_steps: int = 50
) -> Attacker:
    from diffusers import DDIMInverseScheduler, DDIMScheduler, StableDiffusionPipeline

    scheduler = DDIMScheduler.from_pretrained(model_id, subfolder="scheduler", revision=revision)
    inverse = DDIMInverseScheduler.from_pretrained(model_id, subfolder="scheduler", revision=revision)
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id, revision=revision, scheduler=scheduler, safety_checker=None, torch_dtype=torch.float32
    ).to(device)
    pipe.set_progress_bar_config(disable=True)
    return make_attacker(pipe, inverse, num_inversion_steps)


def encode(attacker: Attacker, image: Image.Image) -> torch.Tensor:
    """Image to scaled VAE latent (posterior mean)."""
    pipe = attacker.pipe
    pixels = np.asarray(image.convert("RGB"), dtype=np.float32) / 127.5 - 1.0
    batch = torch.from_numpy(pixels).permute(2, 0, 1).unsqueeze(0).to(device=pipe.device, dtype=pipe.vae.dtype)
    with torch.no_grad():
        latent = pipe.vae.encode(batch).latent_dist.mean
    return latent * pipe.vae.config.scaling_factor


def decode(attacker: Attacker, latents: torch.Tensor) -> Image.Image:
    pipe = attacker.pipe
    with torch.no_grad():
        decoded = pipe.vae.decode(latents.detach() / pipe.vae.config.scaling_factor, return_dict=False)[0]
    pixels = (decoded[0] * 0.5 + 0.5).clamp(0, 1).permute(1, 2, 0).cpu().numpy()
    return Image.fromarray((pixels * 255).round().astype(np.uint8))


def _empty_prompt_embeds(attacker: Attacker) -> torch.Tensor:
    with torch.no_grad():
        embeds, _ = attacker.pipe.encode_prompt("", attacker.pipe.device, 1, False)
    return embeds


def invert(attacker: Attacker, z0: torch.Tensor, prompt_embeds: torch.Tensor, differentiable: bool = False) -> torch.Tensor:
    """DDIM-invert a clean latent to noise with an empty prompt and no guidance."""
    scheduler = attacker.inverse_scheduler
    scheduler.set_timesteps(attacker.num_inversion_steps, device=z0.device)
    unet = attacker.pipe.unet

    def predict_noise(sample, timestep):
        return unet(sample, timestep, encoder_hidden_states=prompt_embeds, return_dict=False)[0]

    latents = z0
    for timestep in scheduler.timesteps:
        model_input = scheduler.scale_model_input(latents, timestep)
        if differentiable:
            # Recompute each UNet call on the backward pass instead of storing its activations.
            noise = checkpoint(predict_noise, model_input, timestep, use_reentrant=False)
        else:
            noise = predict_noise(model_input, timestep)
        latents = scheduler.step(noise, timestep, latents, return_dict=False)[0]
    return latents


def imprint(
    cover: Image.Image,
    reference: Image.Image,
    attacker: Attacker,
    max_steps: int,
    lr: float = 1e-2,
    validate_every: int = 10,
    on_validate: Optional[Callable[[int, Image.Image, float], bool]] = None,
) -> ImprintResult:
    """Optimize the cover's latent until its inverted noise matches the reference's.

    on_validate(step, image, optim_seconds) is called every validate_every steps and at
    max_steps; returning True stops the run.
    """
    if cover.size != reference.size:
        raise ValueError(f"cover and reference sizes differ: {cover.size} vs {reference.size}")
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1")
    if validate_every < 1:
        raise ValueError("validate_every must be at least 1")

    embeds = _empty_prompt_embeds(attacker)
    with torch.no_grad():
        target = invert(attacker, encode(attacker, reference), embeds)
    z0 = torch.nn.Parameter(encode(attacker, cover).clone())
    optimizer = torch.optim.Adam([z0], lr=lr)

    records: list[StepRecord] = []
    optim_seconds = 0.0
    stopped_early = False
    step = 0
    for step in range(1, max_steps + 1):
        started = time.perf_counter()
        optimizer.zero_grad()
        loss = torch.nn.functional.mse_loss(invert(attacker, z0, embeds, differentiable=True), target)
        if not torch.isfinite(loss):
            raise RuntimeError(f"imprint loss is not finite at step {step}")
        loss.backward()
        optimizer.step()
        elapsed = time.perf_counter() - started
        optim_seconds += elapsed
        records.append(StepRecord(step, float(loss.item()), elapsed))
        if on_validate is not None and (step % validate_every == 0 or step == max_steps):
            if on_validate(step, decode(attacker, z0), optim_seconds):
                stopped_early = True
                break
    return ImprintResult(decode(attacker, z0), step, records, stopped_early)
