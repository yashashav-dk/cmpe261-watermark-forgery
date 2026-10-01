"""Summary table and figures from a run log."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from PIL import Image, ImageChops  # noqa: E402

from wmforge.harness import SCHEMES  # noqa: E402
from wmforge.metrics import wilson_interval  # noqa: E402

# Default decision thresholds on the raw detector score, from MarkDiffusion's TR.json and GS.json.
DEFAULT_THRESHOLDS = {"TR": 50.0, "GS": 0.7}
SCHEME_NAMES = {"TR": "Tree-Ring", "GS": "Gaussian Shading"}
SCORE_LABELS = {"TR": "L1 distance to watermark key", "GS": "Bit accuracy"}

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES = "#2a78d6"


def load(csv_path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype={"image_id": str, "scheme": str, "stage": str, "kind": str})
    for column in ("attack", "condition"):
        df[column] = df[column].fillna("").astype(str)
    return df


def _rate(flags) -> str:
    flags = list(flags)
    if not flags:
        return "n/a"
    hits = int(sum(flags))
    low, high = wilson_interval(hits, len(flags))
    return f"{hits}/{len(flags)} = {hits / len(flags):.0%} [{low:.0%}, {high:.0%}]"


def _flagged(frame: pd.DataFrame) -> list[bool]:
    return (frame.is_watermarked == 1).tolist()


def summarize(df: pd.DataFrame) -> list[dict]:
    rows = []
    for scheme in sorted(df.scheme.unique()):
        group = df[df.scheme == scheme]
        clean = group[group.stage == "clean"]
        forged = group[(group.stage == "imprint") & (group.kind == "forged")]
        first_detection = forged[forged.is_watermarked == 1].groupby("image_id").step.min()
        last = forged.sort_values("step").groupby("image_id").tail(1)
        rows.append(
            {
                "Scheme": scheme,
                "TPR, watermarked": _rate(_flagged(clean[clean.kind == "watermarked"])),
                "FPR, unwatermarked": _rate(_flagged(clean[clean.kind == "unwatermarked"])),
                "FPR, real photos": _rate(_flagged(group[group.stage == "real"])),
                "Forgery success (imprint, C1)": _rate((forged.groupby("image_id").is_watermarked.max() == 1).tolist()),
                "Median first-detection step": "n/a" if first_detection.empty else f"{first_detection.median():.0f}",
                "PSNR / SSIM / LPIPS at last step": "n/a"
                if last.empty
                else f"{last.psnr.mean():.1f} dB / {last.ssim.mean():.3f} / {last.lpips.mean():.3f}",
                "Seconds per imprint step": "n/a" if last.empty else f"{(last.seconds / last.step).mean():.1f}",
            }
        )
    return rows


def summary_markdown(df: pd.DataFrame) -> str:
    rows = summarize(df)
    if not rows:
        return "No rows in run log.\n"
    headers = list(rows[0])
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(row[header] for header in headers) + " |" for row in rows]
    return "\n".join(lines) + "\n"


def _style_axis(axis) -> None:
    axis.set_facecolor(SURFACE)
    for side in ("top", "right"):
        axis.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axis.spines[side].set_color(AXIS)
    axis.grid(axis="y", color=GRIDLINE, linewidth=0.8)
    axis.set_axisbelow(True)
    axis.tick_params(colors=INK_MUTED, labelsize=9, length=0)


def plot_trajectories(df: pd.DataFrame, path) -> bool:
    """Detector score against imprint step: one panel per scheme, one line per cover photograph.

    Every cover is the same kind of thing, so all lines share one colour. A filled marker
    means the detector flagged the image as watermarked at that step.
    """
    forged = df[(df.stage == "imprint") & (df.kind == "forged")]
    schemes = sorted(forged.scheme.unique())
    if not schemes:
        return False
    figure, axes = plt.subplots(1, len(schemes), figsize=(5.6 * len(schemes), 4.2), squeeze=False)
    figure.patch.set_facecolor(SURFACE)
    for axis, scheme in zip(axes[0], schemes):
        _style_axis(axis)
        real = df[(df.stage == "real") & (df.scheme == scheme)].set_index("image_id")
        covers = forged[forged.scheme == scheme].groupby("image_id")
        for image_id, cover_rows in covers:
            cover_rows = cover_rows.sort_values("step")
            steps = cover_rows.step.tolist()
            scores = cover_rows.raw_score.tolist()
            flagged = (cover_rows.is_watermarked == 1).tolist()
            if image_id in real.index:
                steps = [0] + steps
                scores = [float(real.raw_score[image_id])] + scores
                flagged = [bool(real.is_watermarked[image_id] == 1)] + flagged
            axis.plot(steps, scores, color=SERIES, linewidth=2, alpha=0.75, zorder=2)
            axis.scatter(
                steps,
                scores,
                s=52,
                facecolors=[SERIES if hit else SURFACE for hit in flagged],
                edgecolors=SERIES,
                linewidths=1.6,
                zorder=3,
            )
        side = "higher" if SCHEMES[scheme].higher_is_watermarked else "lower"
        if scheme in DEFAULT_THRESHOLDS:
            axis.axhline(
                DEFAULT_THRESHOLDS[scheme], color=INK_SECONDARY, linestyle=(0, (4, 3)), linewidth=1.2, zorder=1
            )
        axis.set_title(
            f"{SCHEME_NAMES.get(scheme, scheme)}: {covers.ngroups} cover photographs ({side} = watermarked)",
            fontsize=11,
            color=INK,
            loc="left",
        )
        axis.set_xlabel("Imprint optimization step (0 = untouched photograph)", fontsize=9, color=INK_SECONDARY)
        axis.set_ylabel(SCORE_LABELS.get(scheme, "Detector score"), fontsize=9, color=INK_SECONDARY)
    handles = [
        Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor=SERIES, markeredgecolor=SERIES,
               label="flagged as watermarked"),
        Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor=SURFACE, markeredgecolor=SERIES,
               markeredgewidth=1.6, label="not flagged"),
        Line2D([], [], color=INK_SECONDARY, linestyle=(0, (4, 3)), linewidth=1.2, label="default detection threshold"),
    ]
    figure.legend(
        handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=9, labelcolor=INK_SECONDARY,
        bbox_to_anchor=(0.5, 0.0),
    )
    figure.tight_layout(rect=(0, 0.07, 1, 1))
    figure.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(figure)
    return True


def image_grid(df: pd.DataFrame, images_dir, path, per_scheme: int = 3, gain: int = 4) -> bool:
    """Cover, forged image, and amplified difference for the first covers of each scheme."""
    images_dir = Path(images_dir)
    forged = df[(df.stage == "imprint") & (df.kind == "forged")]
    examples = []
    for scheme in sorted(forged.scheme.unique()):
        taken = 0
        for image_id in forged[forged.scheme == scheme].image_id.drop_duplicates():
            cover_path = images_dir / f"{scheme}_{image_id}_cover.png"
            forged_path = images_dir / f"{scheme}_{image_id}_forged.png"
            if cover_path.exists() and forged_path.exists() and taken < per_scheme:
                examples.append((scheme, image_id, cover_path, forged_path))
                taken += 1
    if not examples:
        return False
    figure, axes = plt.subplots(len(examples), 3, figsize=(9, 3.1 * len(examples)), squeeze=False)
    figure.patch.set_facecolor(SURFACE)
    for row, (scheme, image_id, cover_path, forged_path) in zip(axes, examples):
        cover = Image.open(cover_path).convert("RGB")
        forged_image = Image.open(forged_path).convert("RGB")
        difference = ImageChops.difference(cover, forged_image).point(lambda value: min(255, value * gain))
        titles = (
            f"{SCHEME_NAMES.get(scheme, scheme)}: cover (COCO {image_id})",
            "After imprint",
            f"Absolute difference, x{gain}",
        )
        for axis, image, title in zip(row, (cover, forged_image, difference), titles):
            axis.imshow(image)
            axis.set_title(title, fontsize=9, color=INK, loc="left")
            axis.axis("off")
    figure.tight_layout()
    figure.savefig(path, dpi=120, facecolor=SURFACE)
    plt.close(figure)
    return True


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", default="results/checkin1", help="directory holding runs.csv")
    args = parser.parse_args(argv)
    run_dir = Path(args.run)
    df = load(run_dir / "runs.csv")
    summary = summary_markdown(df)
    (run_dir / "summary.md").write_text(summary, encoding="utf-8")
    plot_trajectories(df, run_dir / "trajectories.png")
    image_grid(df, run_dir / "images", run_dir / "grid.png")
    print(summary)


if __name__ == "__main__":
    main()
