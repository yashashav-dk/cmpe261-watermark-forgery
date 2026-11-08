"""Offline analyses of the Check-in 3 measurement log for the report draft.

These helpers never call a GPU. They recompute forgeability gaps, threshold
disagreements and per-cover quality from results/checkin3/full/measurements-v2.json.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from wmforge.harness import SCHEMES
from wmforge.metrics import bootstrap_ci, wilson_interval

NAMES = {
    "GS": "Gaussian Shading",
    "PRC": "PRC",
    "WIND": "WIND",
    "RI": "Ring-ID",
    "SFW": "SFW",
    "TR": "Tree-Ring",
}
ORDER = list(SCHEMES)
BUDGETS = (50, 100, 150)


def load_rows(path: str | Path) -> list[dict]:
    payload = json.loads(Path(path).read_text())
    if payload.get("schema_version") != 2:
        raise ValueError("expected measurement schema_version 2")
    return payload["rows"]


def load_calibrations(root: str | Path) -> dict[str, dict]:
    root = Path(root)
    out = {}
    for scheme in ORDER:
        path = root / f"{scheme}-calibration.json"
        out[scheme] = json.loads(path.read_text())
    return out


def calibrated_accept(row: dict, calibration: dict) -> bool:
    return row["score"] > calibration["threshold"]


def first_accept_step(rows: Iterable[dict], rule: str, calibration: dict | None = None) -> int | None:
    """Smallest evaluated step at which the chosen rule accepts; None if never."""
    for row in sorted(rows, key=lambda r: r["step"]):
        if rule == "native":
            ok = row["native"]
        elif rule == "calibrated":
            if calibration is None:
                raise ValueError("calibrated rule needs a calibration record")
            ok = calibrated_accept(row, calibration)
        else:
            raise ValueError(f"unknown rule {rule!r}")
        if ok:
            return int(row["step"])
    return None


def forgery_table(rows: list[dict], calibrations: dict[str, dict]) -> list[dict]:
    """Accepted covers at each fixed budget under both decision rules."""
    by = defaultdict(list)
    for row in rows:
        if row["stage"] != "imprint":
            continue
        by[(row["scheme"], row["image_id"])].append(row)

    table = []
    for scheme in ORDER:
        covers = sorted({image_id for (s, image_id) in by if s == scheme})
        for budget in BUDGETS:
            native = 0
            calibrated = 0
            for image_id in covers:
                traj = [r for r in by[(scheme, image_id)] if r["step"] == budget]
                if len(traj) != 1:
                    raise ValueError(f"missing imprint step {budget} for {scheme}/{image_id}")
                row = traj[0]
                native += int(row["native"])
                calibrated += int(calibrated_accept(row, calibrations[scheme]))
            n = len(covers)
            table.append(
                dict(
                    scheme=scheme,
                    name=NAMES[scheme],
                    budget=budget,
                    n=n,
                    native_successes=native,
                    native_wilson95=wilson_interval(native, n),
                    calibrated_successes=calibrated,
                    calibrated_wilson95=wilson_interval(calibrated, n),
                )
            )
    return table


def threshold_disagreement(rows: list[dict], calibrations: dict[str, dict]) -> list[dict]:
    """Counts where native and calibrated verdicts disagree, by stage."""
    out = []
    for scheme in ORDER:
        cal = calibrations[scheme]
        for stage in ("baseline", "imprint", "removal"):
            subset = [r for r in rows if r["scheme"] == scheme and r["stage"] == stage]
            if stage == "imprint":
                subset = [r for r in subset if r["step"] in BUDGETS]
            native_only = 0
            calibrated_only = 0
            for row in subset:
                n_ok = bool(row["native"])
                c_ok = calibrated_accept(row, cal)
                if n_ok and not c_ok:
                    native_only += 1
                if c_ok and not n_ok:
                    calibrated_only += 1
            out.append(
                dict(
                    scheme=scheme,
                    name=NAMES[scheme],
                    stage=stage,
                    observed_n=len(subset),
                    native_only=native_only,
                    calibrated_only=calibrated_only,
                    disagree=native_only + calibrated_only,
                )
            )
    return out


def cover_quality(rows: list[dict]) -> list[dict]:
    """Mean PSNR / SSIM / LPIPS at each budget, pooled across schemes and per cover."""
    by_cover = defaultdict(list)
    by_budget = defaultdict(list)
    for row in rows:
        if row["stage"] != "imprint" or row["step"] not in BUDGETS:
            continue
        by_cover[(row["image_id"], row["step"])].append(row)
        by_budget[row["step"]].append(row)

    per_budget = []
    for budget in BUDGETS:
        group = by_budget[budget]
        psnr = [r["psnr"] for r in group]
        ssim = [r["ssim"] for r in group]
        lpips = [r["lpips"] for r in group]
        per_budget.append(
            dict(
                budget=budget,
                n=len(group),
                psnr_mean=sum(psnr) / len(psnr),
                psnr_bootstrap95=bootstrap_ci(psnr, seed=261),
                ssim_mean=sum(ssim) / len(ssim),
                ssim_bootstrap95=bootstrap_ci(ssim, seed=261),
                lpips_mean=sum(lpips) / len(lpips),
                lpips_bootstrap95=bootstrap_ci(lpips, seed=261),
            )
        )

    per_cover = []
    for (image_id, budget), group in sorted(by_cover.items()):
        psnr = [r["psnr"] for r in group]
        per_cover.append(
            dict(
                image_id=image_id,
                budget=budget,
                n_schemes=len(group),
                psnr_mean=sum(psnr) / len(psnr),
                psnr_min=min(psnr),
                psnr_max=max(psnr),
            )
        )
    return per_budget, per_cover


def forgeability_order(rows: list[dict], calibrations: dict[str, dict]) -> list[dict]:
    """Median first native acceptance step across covers that were accepted by step 150."""
    by = defaultdict(list)
    for row in rows:
        if row["stage"] != "imprint":
            continue
        by[(row["scheme"], row["image_id"])].append(row)

    out = []
    for scheme in ORDER:
        steps = []
        for image_id in sorted({i for (s, i) in by if s == scheme}):
            step = first_accept_step(by[(scheme, image_id)], "native")
            if step is not None:
                steps.append(step)
        steps_sorted = sorted(steps)
        median = None
        if steps_sorted:
            mid = len(steps_sorted) // 2
            if len(steps_sorted) % 2:
                median = steps_sorted[mid]
            else:
                median = 0.5 * (steps_sorted[mid - 1] + steps_sorted[mid])
        out.append(
            dict(
                scheme=scheme,
                name=NAMES[scheme],
                accepted_by_150=len(steps_sorted),
                median_first_native=median,
                min_first_native=min(steps_sorted) if steps_sorted else None,
                max_first_native=max(steps_sorted) if steps_sorted else None,
                calibrated_at_150=sum(
                    1
                    for image_id in sorted({i for (s, i) in by if s == scheme})
                    if calibrated_accept(
                        next(r for r in by[(scheme, image_id)] if r["step"] == 150),
                        calibrations[scheme],
                    )
                ),
            )
        )
    # Easiest to forge first (lowest median first-acceptance step).
    return sorted(
        out,
        key=lambda row: (
            float("inf") if row["median_first_native"] is None else row["median_first_native"],
            -row["accepted_by_150"],
            row["scheme"],
        ),
    )


def removal_split(rows: list[dict], calibrations: dict[str, dict]) -> list[dict]:
    """Native versus calibrated survival under each Check-in 3 removal attack."""
    out = []
    for scheme in ORDER:
        cal = calibrations[scheme]
        for attack in ("jpeg", "blur", "crop", "purification"):
            subset = [
                r
                for r in rows
                if r["scheme"] == scheme
                and r["stage"] == "removal"
                and r["attack"] == attack
            ]
            n = len(subset)
            native = sum(1 for r in subset if r["native"])
            calibrated = sum(1 for r in subset if calibrated_accept(r, cal))
            out.append(
                dict(
                    scheme=scheme,
                    name=NAMES[scheme],
                    attack=attack,
                    n=n,
                    native_successes=native,
                    native_wilson95=wilson_interval(native, n) if n else None,
                    calibrated_successes=calibrated,
                    calibrated_wilson95=wilson_interval(calibrated, n) if n else None,
                    gap=calibrated - native,
                )
            )
    return out


def run_all(measurements: str | Path, calibration_root: str | Path) -> dict:
    rows = load_rows(measurements)
    calibrations = load_calibrations(calibration_root)
    per_budget, per_cover = cover_quality(rows)
    return dict(
        forgery=forgery_table(rows, calibrations),
        disagreement=threshold_disagreement(rows, calibrations),
        quality_by_budget=per_budget,
        quality_by_cover=per_cover,
        forgeability_order=forgeability_order(rows, calibrations),
        removal=removal_split(rows, calibrations),
    )
