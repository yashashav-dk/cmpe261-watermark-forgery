"""Check-in 1 experiment: clean baseline, real-photo baseline, imprint forgery under C1."""
from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from PIL import Image

from wmforge import data, metrics
from wmforge.harness import Detection
from wmforge.records import RunLog

TARGET_MODEL = "Manojb/stable-diffusion-2-1-base"
TARGET_REVISION = "0094d483a120f3f33dafbd187ea4aa60d10de75c"
REFERENCE_SEED_OFFSET = 10_000
STAGES = ("clean", "real", "imprint")


@dataclass(frozen=True)
class RunMeta:
    target_rev: str
    attacker_rev: str = ""


def _row(
    meta: RunMeta,
    *,
    stage: str,
    scheme: str,
    image_id: str,
    kind: str,
    step: int = 0,
    attack: str = "",
    condition: str = "",
    detection=None,
    seed="",
    seconds="",
    loss="",
    psnr="",
    ssim="",
    lpips="",
) -> dict:
    return {
        "stage": stage,
        "scheme": scheme,
        "attack": attack,
        "condition": condition,
        "image_id": image_id,
        "kind": kind,
        "step": step,
        "raw_score": "" if detection is None else detection.raw_score,
        "score": "" if detection is None else detection.score,
        "is_watermarked": "" if detection is None else int(detection.is_watermarked),
        "psnr": psnr,
        "ssim": ssim,
        "lpips": lpips,
        "loss": loss,
        "seconds": seconds,
        "seed": seed,
        "target_rev": meta.target_rev,
        "attacker_rev": meta.attacker_rev,
    }


def run_clean(harness, prompts: Sequence[str], log: RunLog, meta: RunMeta) -> None:
    """Generate a watermarked and an unwatermarked image per prompt and run the detector on both."""
    for index, prompt in enumerate(prompts):
        for kind, watermarked in (("watermarked", True), ("unwatermarked", False)):
            key = dict(
                stage="clean", scheme=harness.scheme, condition="", image_id=f"prompt{index:04d}", kind=kind, step=0
            )
            if log.has(**key):
                continue
            started = time.perf_counter()
            image = harness.generate(prompt, seed=index, watermarked=watermarked)
            detection = harness.detect(image)
            log.append(_row(meta, **key, detection=detection, seed=index, seconds=time.perf_counter() - started))


def run_real(harness, image_ids: Sequence[int], load_cover: Callable, log: RunLog, meta: RunMeta) -> None:
    """Run the detector on untouched real photographs."""
    for image_id in image_ids:
        key = dict(stage="real", scheme=harness.scheme, condition="", image_id=str(image_id), kind="real", step=0)
        if log.has(**key):
            continue
        started = time.perf_counter()
        detection = harness.detect(load_cover(image_id))
        log.append(_row(meta, **key, detection=detection, seconds=time.perf_counter() - started))


def run_imprint(
    harness,
    attacker,
    image_ids: Sequence[int],
    prompts: Sequence[str],
    load_cover: Callable,
    log: RunLog,
    meta: RunMeta,
    images_dir,
    imprint_fn: Callable,
    quality_fn: Callable[[Image.Image, Image.Image], dict],
    max_steps: int = 60,
    validate_every: int = 10,
    stop_on_detect: bool = True,
    condition: str = "C1",
) -> None:
    """Imprint one watermarked reference onto each cover and record the detector's verdict as it goes."""
    if len(prompts) < len(image_ids):
        raise ValueError(f"{len(image_ids)} covers but only {len(prompts)} prompts for references")
    images_dir = Path(images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)

    for index, image_id in enumerate(image_ids):
        base = dict(stage="imprint", scheme=harness.scheme, condition=condition, image_id=str(image_id))
        if log.has(**base, kind="done", step=0):
            continue
        seed = REFERENCE_SEED_OFFSET + index
        reference = harness.generate(prompts[index], seed=seed, watermarked=True)
        log.append(
            _row(meta, **base, attack="imprint", kind="reference", detection=harness.detect(reference), seed=seed)
        )
        cover = load_cover(image_id)
        stem = f"{harness.scheme}_{image_id}"
        reference.save(images_dir / f"{stem}_reference.png")
        cover.save(images_dir / f"{stem}_cover.png")
        last = {}

        def on_validate(step: int, image: Image.Image, optim_seconds: float) -> bool:
            logged = log.get(**base, kind="forged", step=step)
            if logged is not None:
                # An interrupted attempt already recorded this step. Its verdict stands, so the
                # log stays the single record of what was decided.
                detection = Detection(
                    float(logged["raw_score"]), float(logged["score"]), logged["is_watermarked"] == "1"
                )
            else:
                detection = harness.detect(image)
                log.append(
                    _row(
                        meta,
                        **base,
                        attack="imprint",
                        kind="forged",
                        step=step,
                        detection=detection,
                        seed=seed,
                        seconds=optim_seconds,
                        **quality_fn(cover, image),
                    )
                )
            last["detection"] = detection
            return stop_on_detect and detection.is_watermarked

        result = imprint_fn(
            cover, reference, attacker, max_steps=max_steps, validate_every=validate_every, on_validate=on_validate
        )
        result.image.save(images_dir / f"{stem}_forged.png")
        log.append(
            _row(
                meta,
                **base,
                attack="imprint",
                kind="done",
                detection=last.get("detection"),
                seed=seed,
                seconds=sum(record.seconds for record in result.records),
                loss=result.records[-1].loss if result.records else "",
            )
        )


def default_quality(device: str) -> Callable[[Image.Image, Image.Image], dict]:
    def quality(cover: Image.Image, image: Image.Image) -> dict:
        return {
            "psnr": metrics.psnr(cover, image),
            "ssim": metrics.ssim(cover, image),
            "lpips": metrics.lpips_distance(cover, image, device=device),
        }

    return quality


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="results/checkin1")
    parser.add_argument("--schemes", nargs="+", default=["TR", "GS"])
    parser.add_argument("--stages", nargs="+", default=list(STAGES), choices=STAGES)
    parser.add_argument("--n-clean", type=int, default=50)
    parser.add_argument("--n-real", type=int, default=50)
    parser.add_argument("--n-covers", type=int, default=5)
    parser.add_argument("--max-steps", type=int, default=60)
    parser.add_argument("--validate-every", type=int, default=10)
    parser.add_argument("--prompts", default="data/prompts_checkin1.txt")
    parser.add_argument("--image-ids", default="data/coco_val2017_checkin1.txt")
    parser.add_argument("--cache", default="data/.cache/coco")
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args(argv)

    from wmforge import harness as harness_module

    prompts = data.read_lines(args.prompts)
    image_ids = data.read_image_ids(args.image_ids)
    out = Path(args.out)
    log = RunLog(out / "runs.csv")

    def load_cover(image_id: int) -> Image.Image:
        return data.load_cover(image_id, args.cache)

    pipe = harness_module.load_target_pipe(TARGET_MODEL, TARGET_REVISION, args.device)
    attacker = None
    for scheme in args.schemes:
        harness = harness_module.build_harness(scheme, pipe, args.device)
        if "clean" in args.stages:
            run_clean(harness, prompts[: args.n_clean], log, RunMeta(TARGET_REVISION))
        if "real" in args.stages:
            run_real(harness, image_ids[: args.n_real], load_cover, log, RunMeta(TARGET_REVISION))
        if "imprint" in args.stages:
            from wmforge import imprint as imprint_module

            if attacker is None:
                attacker = imprint_module.load_attacker(TARGET_MODEL, TARGET_REVISION, args.device)
            run_imprint(
                harness,
                attacker,
                image_ids[: args.n_covers],
                prompts,
                load_cover,
                log,
                RunMeta(TARGET_REVISION, TARGET_REVISION),
                out / "images",
                imprint_module.imprint,
                default_quality(args.device),
                max_steps=args.max_steps,
                validate_every=args.validate_every,
            )
        print(f"finished {scheme}: {', '.join(args.stages)}")


if __name__ == "__main__":
    main()
