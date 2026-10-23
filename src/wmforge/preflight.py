"""GPU/Drive preflight and measured pilot; never writes full benchmark measurements."""

from __future__ import annotations

import argparse
import gc
import json
import time
from pathlib import Path


from wmforge import benchmark as b, data
from wmforge.checkin3 import check_environment, source_identity, seed_all, single_writer
from wmforge.harness import SCHEMES, build_harness, load_target_pipe
from wmforge.key_state import dump_watermark, load_watermark
from wmforge.smoke import TARGET_MODEL, TARGET_REVISION, default_quality


def run(root, cache):
    root = Path(root)
    if root.exists() and any(p.name != "writer.lock" for p in root.iterdir()):
        raise FileExistsError(
            "pilot directory contains evidence; choose a new directory"
        )
    import torch
    from markdiffusion.evaluation.tools.image_editor import DiffusionPurification
    from wmforge.imprint import load_attacker, imprint

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    pilot = dict(passed=False, source=source_identity(), schemes={}, removal=b.ATTACKS)
    started = time.perf_counter()
    try:
        pilot["environment"] = check_environment()
        pilot["gpu"] = torch.cuda.get_device_name(0)
        pilot["total_gpu_bytes"] = torch.cuda.get_device_properties(0).total_memory
        probe = root / "save-reopen.bin"
        b.atomic_bytes(probe, b"checkin3-save-reopen")
        if probe.read_bytes() != b"checkin3-save-reopen":
            raise RuntimeError("Drive save/reopen check failed")
        cover = data.load_cover(
            data.read_image_ids("data/coco_val2017_checkin1.txt")[0], cache
        )
        prompt = data.read_lines("data/prompts_checkin1.txt")[0]
        pipe = load_target_pipe(TARGET_MODEL, TARGET_REVISION, "cuda")
        for scheme in SCHEMES:
            seed_all(261 + list(SCHEMES).index(scheme))
            harness = build_harness(scheme, pipe, "cuda")
            purifier = DiffusionPurification(
                harness.watermark.config,
                purification_strength=0.3,
                prompt="",
                purifier_pipe=pipe,
            )
            item_started = time.perf_counter()
            before = torch.cuda.max_memory_allocated()
            harness.watermark = load_watermark(
                dump_watermark(harness.watermark, pipe), pipe
            )
            reference = harness.generate(prompt, 261, True)
            unwatermarked = harness.generate(prompt, 100261, False)
            if reference.size != (512, 512) or unwatermarked.size != (512, 512):
                raise RuntimeError("generation dimensions differ from 512x512")
            seed_all(261)
            verdict = harness.detect(reference)
            payload = dump_watermark(harness.watermark, pipe)
            harness.watermark = load_watermark(payload, pipe)
            seed_all(261)
            restored = harness.detect(reference)
            if verdict != restored:
                raise RuntimeError(f"{scheme}: key restoration changed detector result")
            detections = [
                harness.detect(image) for image in (reference, unwatermarked, cover)
            ]
            attacks = {}
            for attack in b.ATTACKS:
                image = b.removal(reference, attack, 261, purifier)
                if image.size != (512, 512):
                    raise RuntimeError("removal dimensions differ")
                key = dict(
                    protocol="checkin3-pilot",
                    scheme=scheme,
                    stage="removal",
                    attack=attack,
                    image_id="pilot",
                    kind="watermarked",
                    step=0,
                )
                measured = b.measurement(
                    harness, image, key, root, f"images/{scheme}_{attack}.png"
                )
                attacks[attack] = dict(
                    score=measured["score"],
                    native=measured["native"],
                    sha256=measured["sha256"],
                )
            attacker = load_attacker(TARGET_MODEL, TARGET_REVISION, "cuda")
            checkpoint = root / f"checkpoints/{scheme}.pt"
            # Pilot trajectories are independent from the full run; reruns time a fresh pilot.
            checkpoint.unlink(missing_ok=True)
            log = b.BenchmarkLog(root / f"{scheme}-pilot-v2.json")
            if log.rows:
                raise RuntimeError(
                    "pilot directory already contains measurements; use a new pilot directory"
                )

            def measure(step, image, seconds, target=harness):
                detection = target.detect(image)
                return dict(
                    protocol="checkin3-pilot",
                    scheme=scheme,
                    stage="imprint",
                    attack="imprint",
                    image_id="pilot",
                    kind="forged",
                    step=step,
                    score=detection.score,
                    native=detection.is_watermarked,
                    seconds=seconds,
                )

            def publish(row, image):
                b.save_image(root, f"images/{scheme}_imprint_{row['step']}.png", image)
                log.append(row)

            attack_started = time.perf_counter()
            result = imprint(
                cover,
                reference,
                attacker,
                max_steps=10,
                lr=0.01,
                validate_every=10,
                checkpoint_path=checkpoint,
                measure=measure,
                publish=publish,
            )
            seconds_per_step = sum(r.seconds for r in result.records) / 10
            # Reopen the checkpoint and replay its measurement without another optimization step.
            resumed = imprint(
                cover,
                reference,
                attacker,
                max_steps=10,
                lr=0.01,
                validate_every=10,
                checkpoint_path=checkpoint,
                measure=measure,
                publish=publish,
            )
            if resumed.image.tobytes() != result.image.tobytes() or len(log.rows) != 1:
                raise RuntimeError("checkpoint replay mismatch")
            quality = default_quality("cuda")(cover, result.image)
            pilot["schemes"][scheme] = dict(
                seconds=time.perf_counter() - item_started,
                seconds_per_imprint_step=seconds_per_step,
                attack_wall_seconds=time.perf_counter() - attack_started,
                peak_gpu_bytes=torch.cuda.max_memory_allocated(),
                initial_gpu_bytes=before,
                scores=[d.score for d in detections],
                native=[d.is_watermarked for d in detections],
                removal=attacks,
                quality=quality,
                key_roundtrip=True,
                checkpoint_roundtrip=True,
            )
            b.atomic_bytes(root / "preflight.json", b.canonical(pilot).encode())
            del attacker, harness, result, resumed, measure, publish, purifier
            gc.collect()
            torch.cuda.empty_cache()
        pilot["estimated_imprint_hours"] = (
            sum(
                v["seconds_per_imprint_step"] * 10 * 150
                for v in pilot["schemes"].values()
            )
            / 3600
        )
        pilot["passed"] = True
    except Exception as error:
        pilot["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        pilot["elapsed_seconds"] = time.perf_counter() - started
        b.atomic_bytes(root / "preflight.json", b.canonical(pilot).encode())
    return pilot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cache", default="data/.cache/coco")
    args = parser.parse_args()
    with single_writer(args.out):
        print(json.dumps(run(args.out, args.cache), indent=2))


if __name__ == "__main__":
    main()
