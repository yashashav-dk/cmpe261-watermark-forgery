"""Prompt and cover-image selection and loading."""
from __future__ import annotations

import random
from pathlib import Path
from typing import Iterable

import requests
from PIL import Image

MARKDIFFUSION_SHA = "9d81656d1a5f9e5194fc2f727bb795ef29e53809"
PROMPTS_URL = (
    "https://github.com/THU-BPM/MarkDiffusion/raw/"
    f"{MARKDIFFUSION_SHA}/dataset/stable_diffusion_prompts/data/eval.parquet"
)
COCO_ANNOTATIONS_URL = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"
COCO_CAPTIONS_MEMBER = "annotations/captions_val2017.json"
IMAGE_SIZE = 512


def select_prompts(prompts: Iterable, n: int, seed: int) -> list[str]:
    """Seeded sample of n prompts after collapsing whitespace and removing blanks and duplicates."""
    cleaned = sorted({" ".join(p.split()) for p in prompts if isinstance(p, str) and p.strip()})
    if n > len(cleaned):
        raise ValueError(f"asked for {n} prompts, only {len(cleaned)} unique non-empty prompts available")
    return random.Random(seed).sample(cleaned, n)


def select_image_ids(ids: Iterable, n: int, seed: int) -> list[int]:
    unique = sorted({int(i) for i in ids})
    if n > len(unique):
        raise ValueError(f"asked for {n} image ids, only {len(unique)} unique ids available")
    return random.Random(seed).sample(unique, n)


def write_lines(path, items) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{item}\n" for item in items), encoding="utf-8")


def read_lines(path) -> list[str]:
    text = Path(path).read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


def read_image_ids(path) -> list[int]:
    return [int(line) for line in read_lines(path)]


def coco_url(image_id: int) -> str:
    return f"http://images.cocodataset.org/val2017/{int(image_id):012d}.jpg"


def center_crop_resize(image: Image.Image, size: int = IMAGE_SIZE) -> Image.Image:
    """Centre-crop to a square and resize, always returning RGB."""
    image = image.convert("RGB")
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return image.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)


def load_cover(image_id: int, cache_dir, size: int = IMAGE_SIZE, timeout: int = 30) -> Image.Image:
    """Return a COCO val2017 photograph as a size x size RGB image, downloading it once."""
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{int(image_id):012d}.jpg"
    if not path.exists():
        response = requests.get(coco_url(image_id), timeout=timeout)
        response.raise_for_status()
        partial = path.with_suffix(".part")
        partial.write_bytes(response.content)
        partial.replace(path)
    with Image.open(path) as image:
        return center_crop_resize(image, size)
