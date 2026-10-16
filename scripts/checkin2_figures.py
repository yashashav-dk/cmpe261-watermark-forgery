"""Draw the Check-in 2 figures from the committed run logs. No GPU needed.

Figure 1: detector scores before any attack, one panel per scheme.
Figure 2: detector score against imprint step, one line per cover photograph.
Figure 3: steps until detection and PSNR of the forgery, one marker per cover.

Sources are fixed in SOURCES: Gaussian Shading and Tree-Ring baselines from the Check-in 1 run,
the Tree-Ring imprint from the 150-step rerun (its step 0 is the same photograph's Check-in 1 detection),
and the other four schemes from the Check-in 2 run.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from wmforge import report  # noqa: E402
from wmforge.harness import SCHEMES  # noqa: E402

SOURCES = [
    ("GS", "results/checkin1", None),
    ("TR", "results/checkin1", ["clean", "real"]),
    ("TR", "results/tr150", ["imprint"]),
    ("RI", "results/checkin2", None),
    ("SFW", "results/checkin2", None),
    ("WIND", "results/checkin2", None),
    ("PRC", "results/checkin2", None),
]
ORDER = ["GS", "PRC", "WIND", "RI", "SFW", "TR"]  # easiest to hardest to forge
THRESHOLDS = {"GS": 0.7, "WIND": 0.5, "TR": 50.0, "RI": 50.0, "SFW": 50.0}
SCORE_LABELS = {
    "GS": "bit accuracy",
    "PRC": "PRC score",
    "WIND": "cosine similarity",
    "TR": "L1 distance",
    "RI": "L1 distance",
    "SFW": "L1 distance",
}
CAP = {"GS": 60, "TR": 150, "RI": 150, "SFW": 150, "WIND": 150, "PRC": 150}
KIND_COLORS = {"watermarked": "#2a78d6", "unwatermarked": "#e8622a", "real": "#27b07a"}
COVER_STYLE = [("#2a78d6", "o"), ("#e8622a", "s"), ("#27b07a", "^"), ("#f0a500", "D"), ("#e86fa0", "v")]
SURFACE, INK, MUTED, GRID = report.SURFACE, report.INK, report.INK_MUTED, report.GRIDLINE


def load_all(root: Path) -> pd.DataFrame:
    frames = [(scheme, report.load(root / run / "runs.csv"), stages) for scheme, run, stages in SOURCES]
    return report.combine_runs(frames)


def name(scheme: str) -> str:
    return report.SCHEME_NAMES.get(scheme, scheme)


def flag_text(scheme: str) -> str:
    if scheme not in THRESHOLDS:
        return f"{SCORE_LABELS[scheme]} · verdict only (direction unverified)"
    side = "above" if SCHEMES[scheme].higher_is_watermarked else "below"
    return f"{SCORE_LABELS[scheme]} · flagged if {side} {THRESHOLDS[scheme]:g}"


def style(axis) -> None:
    axis.set_facecolor(SURFACE)
    for side in ("top", "right"):
        axis.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axis.spines[side].set_color(report.AXIS)
    axis.tick_params(colors=MUTED, labelsize=12, length=0)
    axis.set_axisbelow(True)


def figure_baselines(df: pd.DataFrame, path: Path) -> None:
    rng = np.random.default_rng(0)
    figure, axes = plt.subplots(2, 3, figsize=(20, 11))
    figure.patch.set_facecolor(SURFACE)
    rows = [("watermarked", "Watermarked"), ("unwatermarked", "Unwatermarked"), ("real", "Real photos")]
    for axis, scheme in zip(axes.flat, ORDER):
        style(axis)
        axis.grid(axis="x", color=GRID, linewidth=0.8)
        group = df[df.scheme == scheme]
        for y, (kind, label) in enumerate(reversed(rows)):
            part = group[(group.stage == "clean") & (group.kind == kind)] if kind != "real" else group[group.stage == "real"]
            flagged = part.is_watermarked == 1
            color = KIND_COLORS[kind]
            jitter = rng.uniform(-0.12, 0.12, len(part))
            axis.scatter(part.raw_score, y + jitter, s=60, facecolors=[color if f else SURFACE for f in flagged],
                         edgecolors=color, linewidths=1.6, zorder=3)
            axis.text(1.02, y, f"{int(flagged.sum())}/{len(part)}", transform=axis.get_yaxis_transform(),
                      fontsize=13, color=report.INK_SECONDARY, va="center")
        axis.set_yticks(range(3))
        axis.set_yticklabels([label for _, label in reversed(rows)] if scheme in ("GS", "RI") else [""] * 3,
                             fontsize=14, color=MUTED)
        axis.set_ylim(-0.6, 2.6)
        if scheme in THRESHOLDS:
            axis.axvline(THRESHOLDS[scheme], color=INK, linestyle=(0, (4, 3)), linewidth=1.6, zorder=2)
        axis.set_title(name(scheme), fontsize=17, fontweight="bold", color=INK, loc="left")
        axis.set_xlabel(flag_text(scheme), fontsize=13, color=report.INK_SECONDARY)
    figure.suptitle("Detectors before any attack: every scheme separates watermarked images from real photos",
                    fontsize=20, fontweight="bold", color=INK, x=0.01, ha="left")
    figure.text(0.01, 0.01, "Filled = detector says watermarked; hollow = not. Count at right = flagged / total. "
                "Dashed line = decision threshold.\nGS and TR from Check-in 1; PRC, WIND, RI, SFW from Check-in 2. "
                "50 images per row.", fontsize=12, color=MUTED)
    figure.tight_layout(rect=(0, 0.05, 1, 0.95))
    figure.savefig(path, dpi=100, facecolor=SURFACE)
    plt.close(figure)


def cover_trajectories(df: pd.DataFrame, scheme: str) -> dict[str, pd.DataFrame]:
    group = df[df.scheme == scheme]
    real = group[group.stage == "real"].set_index("image_id")
    forged = group[(group.stage == "imprint") & (group.kind == "forged")]
    out = {}
    for image_id, rows in forged.groupby("image_id"):
        rows = rows.sort_values("step")[["step", "raw_score", "is_watermarked", "psnr"]]
        if image_id in real.index:
            start = pd.DataFrame([{"step": 0, "raw_score": float(real.raw_score[image_id]),
                                   "is_watermarked": int(real.is_watermarked[image_id]), "psnr": np.nan}])
            rows = pd.concat([start, rows], ignore_index=True)
        out[str(image_id)] = rows
    return out


def covers_in_order(df: pd.DataFrame) -> list[str]:
    ids = df[(df.stage == "imprint") & (df.kind == "forged")].image_id.astype(str).unique()
    return sorted(ids, key=int)


def figure_trajectories(df: pd.DataFrame, path: Path) -> None:
    covers = covers_in_order(df)
    styles = dict(zip(covers, COVER_STYLE))
    figure, axes = plt.subplots(2, 3, figsize=(20, 12))
    figure.patch.set_facecolor(SURFACE)
    total_forged = total = 0
    for axis, scheme in zip(axes.flat, ORDER):
        style(axis)
        axis.grid(color=GRID, linewidth=0.8)
        trajectories = cover_trajectories(df, scheme)
        forged_count = sum(int((t.is_watermarked == 1).any()) for t in trajectories.values())
        total_forged += forged_count
        total += len(trajectories)
        for image_id, rows in trajectories.items():
            color, marker = styles[image_id]
            axis.plot(rows.step, rows.raw_score, color=color, linewidth=2.2, zorder=2)
            axis.scatter(rows.step, rows.raw_score, s=90, marker=marker,
                         facecolors=[color if f else SURFACE for f in rows.is_watermarked == 1],
                         edgecolors=color, linewidths=1.8, zorder=3)
        if scheme in THRESHOLDS:
            axis.axhline(THRESHOLDS[scheme], color=INK, linestyle=(0, (4, 3)), linewidth=1.6, zorder=1)
            axis.text(1.01, THRESHOLDS[scheme], f"{THRESHOLDS[scheme]:g}", transform=axis.get_yaxis_transform(),
                      fontsize=13, color=INK, va="center")
        else:
            axis.text(0.02, 0.97, "no fixed threshold; verdict per marker", transform=axis.transAxes,
                      fontsize=12, color=MUTED, va="top")
        if not SCHEMES[scheme].higher_is_watermarked:
            axis.invert_yaxis()
            axis.set_ylabel(f"{SCORE_LABELS[scheme]} (axis flipped)", fontsize=13, color=report.INK_SECONDARY)
        else:
            axis.set_ylabel(SCORE_LABELS[scheme], fontsize=13, color=report.INK_SECONDARY)
        axis.set_xlabel("imprint step", fontsize=13, color=report.INK_SECONDARY)
        axis.set_title(f"{name(scheme)}  ·  {forged_count}/{len(trajectories)} forged", fontsize=17,
                       fontweight="bold", color=INK, loc="left")
    handles = [Line2D([], [], color=c, marker=m, markersize=10, linewidth=2.2, label=f"COCO {image_id}")
               for image_id, (c, m) in styles.items()]
    figure.legend(handles=handles, loc="upper right", ncol=len(handles), frameon=False, fontsize=13,
                  bbox_to_anchor=(0.99, 0.95))
    figure.suptitle(f"Imprint forgery: all {total} attacks moved a real photo toward the watermark; "
                    f"{total_forged} crossed the threshold", fontsize=20, fontweight="bold", color=INK, x=0.01,
                    ha="left")
    figure.text(0.01, 0.01, "Step 0 = untouched real photo. Filled marker = detector says watermarked; the run stops "
                "at the first detection. Up = toward detection on every panel. Same five COCO photos for every\n"
                "scheme. GS and TR from Check-in 1 (TR from the 150-step rerun).", fontsize=12, color=MUTED)
    figure.tight_layout(rect=(0, 0.05, 1, 0.92))
    figure.savefig(path, dpi=100, facecolor=SURFACE)
    plt.close(figure)


def stop_points(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (scheme, cover): step and PSNR where the run stopped, and whether it was forged."""
    rows = []
    for scheme in ORDER:
        for image_id, t in cover_trajectories(df, scheme).items():
            hits = t[t.is_watermarked == 1]
            stop = hits.iloc[0] if not hits.empty else t.iloc[-1]
            rows.append(dict(scheme=scheme, cover=image_id, step=int(stop.step), psnr=float(stop.psnr),
                             forged=not hits.empty))
    return pd.DataFrame(rows)


def figure_cost(df: pd.DataFrame, path: Path) -> None:
    points = stop_points(df)
    covers = covers_in_order(df)
    styles = dict(zip(covers, COVER_STYLE))
    figure, (left, right) = plt.subplots(1, 2, figsize=(20, 7.2))
    figure.patch.set_facecolor(SURFACE)
    ypos = {scheme: len(ORDER) - 1 - i for i, scheme in enumerate(ORDER)}
    offsets = dict(zip(covers, np.linspace(0.18, -0.18, len(covers))))
    for axis, column in ((left, "step"), (right, "psnr")):
        style(axis)
        axis.grid(axis="x", color=GRID, linewidth=0.8)
        for _, p in points.iterrows():
            color, marker = styles[p.cover]
            axis.scatter(p[column], ypos[p.scheme] + offsets[p.cover], s=120, marker=marker,
                         facecolors=color if p.forged else SURFACE, edgecolors=color, linewidths=1.8, zorder=3)
        axis.set_yticks(list(ypos.values()))
        axis.set_yticklabels([name(s) for s in ypos] if axis is left else [""] * len(ypos), fontsize=14, color=MUTED)
        axis.set_ylim(-0.6, len(ORDER) - 0.4)
    for scheme in ORDER:
        part = points[points.scheme == scheme]
        left.text(1.01, ypos[scheme], f"{int(part.forged.sum())}/{len(part)}", transform=left.get_yaxis_transform(),
                  fontsize=13, color=report.INK_SECONDARY, va="center")
    left.set_title("Steps to forge", fontsize=17, fontweight="bold", color=INK, loc="left")
    left.set_xlabel("imprint steps until detected (hollow = not detected by step 150)", fontsize=13,
                    color=report.INK_SECONDARY)
    right.axvline(25, color=MUTED, linestyle=(0, (1, 2)), linewidth=1.6, zorder=1)
    right.text(25, len(ORDER) - 0.3, "~25 dB", fontsize=12, color=MUTED, ha="left", va="bottom")
    right.set_title("Damage to the photo", fontsize=17, fontweight="bold", color=INK, loc="left")
    right.set_xlabel("PSNR of the forged photo vs the original (dB, higher = less visible damage)", fontsize=13,
                     color=report.INK_SECONDARY)
    handles = [Line2D([], [], color=c, marker=m, markersize=10, linewidth=2.2, label=f"COCO {image_id}")
               for image_id, (c, m) in styles.items()]
    figure.legend(handles=handles, loc="lower center", ncol=len(handles), frameon=False, fontsize=13,
                  bbox_to_anchor=(0.5, 0.0))
    figure.suptitle("Wider detector margins slow forgery down but do not stop it", fontsize=20, fontweight="bold",
                    color=INK, x=0.01, ha="left")
    figure.tight_layout(rect=(0, 0.08, 1, 0.93))
    figure.savefig(path, dpi=100, facecolor=SURFACE)
    plt.close(figure)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root holding results/")
    parser.add_argument("--out", default="results/checkin2/figures")
    args = parser.parse_args(argv)
    root = Path(args.root)
    df = load_all(root)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    figure_baselines(df, out / "fig1_baselines.png")
    figure_trajectories(df, out / "fig2_trajectories.png")
    figure_cost(df, out / "fig3_cost.png")
    points = stop_points(df)
    for scheme in ORDER:
        part = points[points.scheme == scheme]
        print(f"{name(scheme):17s} forged {int(part.forged.sum())}/{len(part)}  "
              f"step median {part.step.median():.0f} ({part.step.min()} to {part.step.max()})  "
              f"PSNR median {part.psnr.median():.1f} dB")
    print("wrote", out)


if __name__ == "__main__":
    main()
