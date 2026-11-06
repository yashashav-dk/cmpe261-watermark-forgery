"""Check-in 4 runners: imprint under C2, and strength sweeps for crop / purification.

Reuses the Check-in 3 provider keys, covers and calibrated thresholds. The C2
attacker is Stable Diffusion 1.5 (project-spec T1). Strength sweeps re-open the
saved watermarked baselines and re-detect after each parameterized attack.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
from pathlib import Path

from PIL import Image

from wmforge import benchmark as b
from wmforge.harness import SCHEMES
from wmforge.models import TARGET, resolve_attacker
from wmforge.sweep import (
    CROP_RATIOS,
    PURIFICATION_STRENGTHS,
    run_crop_sweep,
    sweep_key,
)


PROTOCOL = "checkin4-v1"


def load_checkin3_calibration(root: Path, scheme: str) -> dict:
    path = root / f"{scheme}-calibration.json"
    if not path.exists():
        raise FileNotFoundError(f"missing Check-in 3 calibration: {path}")
    return json.loads(path.read_text())


def require_included(calibration: dict, scheme: str) -> None:
    if not calibration.get("included"):
        raise ValueError(f"{scheme} was excluded at Check-in 3; refusing C2 / sweep")


def run_c2_imprint(args):
    """Imprint the same ten covers with an SD 1.5 attacker; detect with the provider."""
    from wmforge.checkin3 import run_forgery, seed_all, source_identity
    from wmforge.data import MARKDIFFUSION_SHA
    from wmforge.harness import build_harness, load_target_pipe
    from wmforge.imprint import load_attacker
    from wmforge.key_state import restore_or_save
    import torch

    checkin3 = Path(args.checkin3)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    cover_ids = Path("data/coco_val2017_checkin3.txt").read_text().splitlines()[:10]
    if len(cover_ids) != 10:
        raise ValueError(f"need 10 covers, found {len(cover_ids)}")

    prompts = Path("data/prompts_checkin3.txt").read_text().splitlines()
    attacker_spec = resolve_attacker("C2")
    identity = dict(
        protocol=PROTOCOL,
        condition="C2",
        provider_model=TARGET.model_id,
        provider_revision=TARGET.revision,
        attacker_model=attacker_spec.model_id,
        attacker_revision=attacker_spec.revision,
        markdiffusion=MARKDIFFUSION_SHA,
        source=source_identity(),
        covers=cover_ids,
        seed=261,
        max_steps=150,
        validate_every=10,
        checkin3_dir=str(checkin3.resolve()),
    )
    b.bind_manifest(out / "manifest.json", identity)
    log = b.BenchmarkLog(out / "measurements-v2.json")

    def load_cover(image_id):
        path = checkin3 / f"inputs/{image_id}.png"
        if not path.exists():
            path = out / f"inputs/{image_id}.png"
        with Image.open(path) as image:
            return image.convert("RGB")

    pipe = load_target_pipe(TARGET.model_id, TARGET.revision, "cuda")
    for scheme in args.schemes:
        calibration = load_checkin3_calibration(checkin3, scheme)
        require_included(calibration, scheme)
        b.bind_manifest(out / f"{scheme}-calibration.json", calibration)
        seed_all(261 + list(SCHEMES).index(scheme))
        harness = build_harness(scheme, pipe, "cuda")
        keypath = checkin3 / f"keys/{scheme}.pkl"
        if not keypath.exists():
            raise FileNotFoundError(f"missing Check-in 3 key: {keypath}")
        restore_or_save(harness, pipe, keypath)
        attacker = load_attacker(
            attacker_spec.model_id, attacker_spec.revision, "cuda"
        )
        run_forgery(
            harness, attacker, cover_ids, prompts, load_cover, log, out
        )
        # Tag every new imprint row with condition C2 via a sidecar index.
        del attacker
        del harness
        gc.collect()
        torch.cuda.empty_cache()
        print(f"finished C2 imprint for {scheme}", flush=True)

    (out / "condition.json").write_text(
        json.dumps({"condition": "C2", "attacker": attacker_spec.__dict__}, indent=2)
    )


def run_purification_sweep(harness, log, root, pipe, strengths=PURIFICATION_STRENGTHS):
    from markdiffusion.evaluation.tools.image_editor import DiffusionPurification
    from wmforge.checkin3 import seed_all

    sources = [
        r
        for r in log.rows
        if r["scheme"] == harness.scheme
        and r["stage"] == "baseline"
        and r["kind"] == "watermarked"
    ]
    if not sources:
        # Fall back to reading artifacts listed in an external Check-in 3 log.
        raise ValueError(f"no watermarked baselines for {harness.scheme}")
    for strength in strengths:
        purifier = DiffusionPurification(
            harness.watermark.config,
            purification_strength=float(strength),
            prompt="",
            purifier_pipe=pipe,
        )
        for source in sources:
            key = sweep_key(harness.scheme, "purification", strength, source["image_id"])
            old = log.get(**key)
            if old:
                b.verify_artifact(root, old)
                continue
            b.verify_artifact(root, source)
            with Image.open(Path(root) / source["artifact"]) as image:
                seed_all(source["seed"])
                transformed = purifier.edit(image.convert("RGB"), prompt="")
            relative = (
                f"images/{harness.scheme}/sweep/purification_{strength:g}_"
                f"{source['image_id']}.png"
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
        del purifier


def run_sweeps(args):
    from wmforge.checkin3 import seed_all
    from wmforge.harness import build_harness, load_target_pipe
    from wmforge.key_state import restore_or_save
    import torch

    checkin3 = Path(args.checkin3)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    # Sweeps read baseline artifacts from the Check-in 3 tree and write into out/.
    identity = dict(
        protocol="checkin4-sweep-v1",
        provider_model=TARGET.model_id,
        provider_revision=TARGET.revision,
        crop_ratios=list(CROP_RATIOS),
        purification_strengths=list(PURIFICATION_STRENGTHS),
        checkin3_dir=str(checkin3.resolve()),
    )
    b.bind_manifest(out / "manifest.json", identity)

    # Copy measurement references: start a fresh sweep log; baseline rows are
    # borrowed by pointing artifact paths at the Check-in 3 root through a
    # symlink when needed.
    images = out / "images"
    if not images.exists():
        images.symlink_to((checkin3 / "images").resolve(), target_is_directory=True)
    # Seed the sweep log with the Check-in 3 baseline rows so run_crop_sweep can
    # find sources, without rewriting the original file.
    base_log = b.BenchmarkLog(checkin3 / "measurements-v2.json")
    log = b.BenchmarkLog(out / "measurements-v2.json")
    for row in base_log.rows:
        if row["stage"] == "baseline" and row["kind"] == "watermarked":
            if log.get(**{k: row[k] for k in b.KEYS}) is None:
                # Re-key protocol for the sweep log while keeping artifact paths.
                transplanted = dict(row)
                transplanted["protocol"] = "checkin4-sweep-v1"
                try:
                    log.append(transplanted)
                except ValueError:
                    pass

    pipe = load_target_pipe(TARGET.model_id, TARGET.revision, "cuda")
    for scheme in args.schemes:
        calibration = load_checkin3_calibration(checkin3, scheme)
        require_included(calibration, scheme)
        seed_all(261 + list(SCHEMES).index(scheme))
        harness = build_harness(scheme, pipe, "cuda")
        restore_or_save(harness, pipe, checkin3 / f"keys/{scheme}.pkl")
        if "crop" in args.attacks:
            run_crop_sweep(harness, log, out, CROP_RATIOS)
        if "purification" in args.attacks:
            run_purification_sweep(harness, log, out, pipe, PURIFICATION_STRENGTHS)
        del harness
        gc.collect()
        torch.cuda.empty_cache()
        print(f"finished sweeps for {scheme}", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    c2 = sub.add_parser("c2-imprint", help="Imprint forgery with SD 1.5 attacker")
    c2.add_argument("--checkin3", type=Path, default=Path("results/checkin3/full"))
    c2.add_argument("--out", type=Path, default=Path("results/checkin4/c2"))
    c2.add_argument("--schemes", nargs="+", choices=list(SCHEMES), default=list(SCHEMES))

    sweeps = sub.add_parser("sweep", help="Crop and purification strength sweeps")
    sweeps.add_argument("--checkin3", type=Path, default=Path("results/checkin3/full"))
    sweeps.add_argument("--out", type=Path, default=Path("results/checkin4/sweeps"))
    sweeps.add_argument("--schemes", nargs="+", choices=list(SCHEMES), default=list(SCHEMES))
    sweeps.add_argument(
        "--attacks", nargs="+", choices=["crop", "purification"], default=["crop", "purification"]
    )

    args = parser.parse_args(argv)
    if args.command == "c2-imprint":
        run_c2_imprint(args)
    elif args.command == "sweep":
        run_sweeps(args)
    else:
        raise SystemExit(f"unknown command {args.command}")


if __name__ == "__main__":
    main()
