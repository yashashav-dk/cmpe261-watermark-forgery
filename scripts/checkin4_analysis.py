"""Recompute Check-in 4 offline tables and figures from the Check-in 3 log.

Usage:
    python scripts/checkin4_analysis.py
    python scripts/checkin4_analysis.py --measurements results/checkin3/full/measurements-v2.json \
        --calibration-root results/checkin3/full --out results/checkin4/analysis
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from wmforge.analysis import NAMES, ORDER, run_all


def write_markdown(analysis: dict, path: Path) -> None:
    lines = [
        "# Check-in 4 offline analysis of the Check-in 3 floor",
        "",
        "Recomputed from `results/checkin3/full/measurements-v2.json`. No new GPU work.",
        "",
        "## Forgeability order (native first acceptance)",
        "",
        "| Scheme | Accepted by step 150 | Median first step | Range | Calibrated at step 150 |",
        "|---|---|---|---|---|",
    ]
    for row in analysis["forgeability_order"]:
        lines.append(
            f"| {row['name']} | {row['accepted_by_150']}/10 | {row['median_first_native']} | "
            f"{row['min_first_native']} to {row['max_first_native']} | {row['calibrated_at_150']}/10 |"
        )
    lines += [
        "",
        "## Native versus calibrated disagreement",
        "",
        "| Scheme | Stage | N | Native only | Calibrated only | Disagree |",
        "|---|---|---|---|---|---|",
    ]
    for row in analysis["disagreement"]:
        lines.append(
            f"| {row['name']} | {row['stage']} | {row['observed_n']} | "
            f"{row['native_only']} | {row['calibrated_only']} | {row['disagree']} |"
        )
    lines += [
        "",
        "## Removal survival gap (calibrated minus native)",
        "",
        "| Scheme | Attack | Native | Calibrated | Gap |",
        "|---|---|---|---|---|",
    ]
    for row in analysis["removal"]:
        lines.append(
            f"| {row['name']} | {row['attack']} | {row['native_successes']}/{row['n']} | "
            f"{row['calibrated_successes']}/{row['n']} | {row['gap']:+d} |"
        )
    lines += [
        "",
        "## Image quality pooled across schemes",
        "",
        "| Budget | N | Mean PSNR (dB) | Mean SSIM | Mean LPIPS |",
        "|---|---|---|---|---|",
    ]
    for row in analysis["quality_by_budget"]:
        lines.append(
            f"| step {row['budget']} | {row['n']} | {row['psnr_mean']:.2f} | "
            f"{row['ssim_mean']:.3f} | {row['lpips_mean']:.3f} |"
        )
    path.write_text("\n".join(lines) + "\n")


def draw_figures(analysis: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)

    # Figure A: median first native acceptance.
    order = analysis["forgeability_order"]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    names = [r["name"] for r in order]
    medians = [r["median_first_native"] if r["median_first_native"] is not None else 0 for r in order]
    accepted = [r["accepted_by_150"] for r in order]
    bars = ax.bar(names, medians, color="#4c78a8")
    for bar, n in zip(bars, accepted):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2, f"{n}/10", ha="center", fontsize=8)
    ax.set_ylabel("Median first native acceptance step")
    ax.set_ylim(0, 160)
    ax.set_title("C1 forgeability order on ten covers")
    fig.tight_layout()
    fig.savefig(out / "figA_forgeability_order.png", dpi=160)
    plt.close(fig)

    # Figure B: disagreement heat-ish bars for imprint budgets.
    imprint = [r for r in analysis["disagreement"] if r["stage"] == "imprint"]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    x = np.arange(len(imprint))
    ax.bar(x - 0.2, [r["native_only"] for r in imprint], width=0.4, label="native only", color="#e45756")
    ax.bar(x + 0.2, [r["calibrated_only"] for r in imprint], width=0.4, label="calibrated only", color="#72b7b2")
    ax.set_xticks(x)
    ax.set_xticklabels([r["name"] for r in imprint], rotation=15)
    ax.set_ylabel("Disagreements at budgets 50/100/150")
    ax.legend(frameon=False)
    ax.set_title("Where the two decision rules disagree on forgeries")
    fig.tight_layout()
    fig.savefig(out / "figB_threshold_disagreement.png", dpi=160)
    plt.close(fig)

    # Figure C: purification gap.
    pur = [r for r in analysis["removal"] if r["attack"] == "purification"]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    x = np.arange(len(pur))
    ax.bar(x - 0.2, [r["native_successes"] for r in pur], width=0.4, label="native", color="#4c78a8")
    ax.bar(x + 0.2, [r["calibrated_successes"] for r in pur], width=0.4, label="calibrated", color="#f58518")
    ax.set_xticks(x)
    ax.set_xticklabels([r["name"] for r in pur], rotation=15)
    ax.set_ylabel("Still detected after purification (of 100)")
    ax.legend(frameon=False)
    ax.set_title("Purification: native verdict versus calibrated score")
    fig.tight_layout()
    fig.savefig(out / "figC_purification_gap.png", dpi=160)
    plt.close(fig)

    # Figure D: per-cover PSNR at step 150.
    covers = [r for r in analysis["quality_by_cover"] if r["budget"] == 150]
    covers = sorted(covers, key=lambda r: r["psnr_mean"], reverse=True)
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.bar([c["image_id"] for c in covers], [c["psnr_mean"] for c in covers], color="#54a24b")
    ax.set_ylabel("Mean PSNR across six schemes (dB)")
    ax.set_xlabel("COCO cover id")
    ax.tick_params(axis="x", rotation=45)
    ax.set_title("Perceptual cost at step 150 is cover-dependent")
    fig.tight_layout()
    fig.savefig(out / "figD_cover_psnr.png", dpi=160)
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--measurements",
        default="results/checkin3/full/measurements-v2.json",
    )
    parser.add_argument(
        "--calibration-root",
        default="results/checkin3/full",
    )
    parser.add_argument("--out", default="results/checkin4/analysis")
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    analysis = run_all(args.measurements, args.calibration_root)
    (out / "analysis.json").write_text(json.dumps(analysis, indent=2))
    write_markdown(analysis, out / "summary.md")
    draw_figures(analysis, Path("results/checkin4/figures"))
    print("wrote", out / "analysis.json")
    print("wrote", out / "summary.md")
    print("wrote figures under results/checkin4/figures/")


if __name__ == "__main__":
    main()
