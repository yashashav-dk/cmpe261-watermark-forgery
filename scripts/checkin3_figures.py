"""Draw the Check-in 3 report figures from the versioned measurement log. No GPU needed.

Usage:
    python scripts/checkin3_figures.py --run results/checkin3/full --out results/checkin3/full/figures
    python scripts/checkin3_figures.py --run RUN_DIR --images RUN_DIR --out OUT   # also draws the image strips

The run directory holds measurements-v2.json and the per-scheme calibration files. The
example-image figures need the saved images (kept out of the repository), so they are
drawn only when --images points at a run directory that has them.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

ORDER = ["GS", "PRC", "WIND", "RI", "SFW", "TR"]  # Check-in 2 order: easiest to hardest to forge
NAMES = {
    "GS": "Gaussian Shading",
    "PRC": "PRC",
    "WIND": "WIND",
    "RI": "Ring-ID",
    "SFW": "SFW",
    "TR": "Tree-Ring",
}
# Native MarkDiffusion decision on the raw score; every logged verdict agrees with these.
THRESH = {
    "GS": (0.7, "above"),
    "WIND": (0.5, "above"),
    "RI": (50.0, "below"),
    "SFW": (50.0, "below"),
    "TR": (50.0, "below"),
    "PRC": (None, None),
}
SCORE_LABEL = {
    "GS": "bit accuracy",
    "WIND": "cosine similarity",
    "RI": "L1 distance",
    "SFW": "L1 distance",
    "TR": "L1 distance",
    "PRC": "PRC score",
}
ATTACKS = [("jpeg", "JPEG q95"), ("blur", "Blur r2"), ("crop", "Crop 0.8"), ("purification", "Purify 0.3")]

INK, INK2, MUTED, GRID = "#1f1f1e", "#55544f", "#8a8983", "#e6e5e0"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4",
          "#7b5cd6", "#14a3b8", "#a6761d", "#5b6b7a", "#c03b3b"]
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "h", "<", ">"]
KINDS = [("watermarked", "Watermarked"), ("unwatermarked", "Unwatermarked"), ("real", "Real photos")]


def load(run: Path):
    rows = pd.DataFrame(json.loads((run / "measurements-v2.json").read_text())["rows"])
    rows["image_id"] = rows["image_id"].astype(str)
    calibration = {s: json.loads((run / f"{s}-calibration.json").read_text()) for s in ORDER}
    covers = [str(c) for c in json.loads((run / "manifest.json").read_text())["image_ids"][:10]]
    return rows, calibration, covers


def raw_threshold(scheme, calibration):
    """Calibrated threshold on the raw-score axis (distance scores were negated for calibration)."""
    t = calibration[scheme]["threshold"]
    return -t if THRESH[scheme][1] == "below" else t


def calibrated(rows, scheme, calibration):
    return rows["score"] > calibration[scheme]["threshold"]


def style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK2,
        "axes.titlecolor": INK,
        "axes.titlesize": 10,
        "axes.titleweight": "bold",
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def threshold_lines(ax, scheme, calibration, horizontal=True):
    line = ax.axhline if horizontal else ax.axvline
    t, _ = THRESH[scheme]
    if t is not None:
        line(t, color=INK, lw=1, ls=(0, (4, 3)), zorder=1)
    line(raw_threshold(scheme, calibration), color=SERIES[1], lw=1, ls=(0, (1, 2)), zorder=1)


def fig_baselines(rows, calibration, out):
    fig, axes = plt.subplots(2, 3, figsize=(10, 5.8))
    rng = np.random.default_rng(0)
    for ax, scheme in zip(axes.flat, ORDER):
        g = rows[(rows.scheme == scheme) & (rows.stage == "baseline")]
        for i, (kind, _) in enumerate(KINDS):
            v = g[g.kind == kind]
            y = i + rng.uniform(-0.2, 0.2, len(v))
            det = v.native.to_numpy(bool)
            ax.scatter(v.raw_score[~det], y[~det], s=12, facecolors="white", edgecolors=SERIES[i], lw=1.0, zorder=3)
            ax.scatter(v.raw_score[det], y[det], s=12, color=SERIES[i], zorder=3)
            ax.text(1.0, i, f" {det.sum()}/{len(v)}", transform=ax.get_yaxis_transform(), ha="left",
                    va="center", color=INK2, fontsize=8, clip_on=False)
        threshold_lines(ax, scheme, calibration, horizontal=False)
        ax.set_yticks(range(3), [k[1] for k in KINDS])
        ax.set_ylim(2.6, -0.6)
        ax.grid(axis="y", visible=False)
        t, side = THRESH[scheme]
        sub = f"flagged if {side} {t:g}" if t is not None else "native decoder verdict"
        ax.set_title(NAMES[scheme], loc="left")
        ax.set_xlabel(f"{SCORE_LABEL[scheme]} · {sub}", fontsize=8)
        if scheme == "PRC":
            ax.ticklabel_format(axis="x", style="plain")
            ax.xaxis.set_major_locator(plt.MaxNLocator(4))
    for ax in axes[:, 1:].flat:
        ax.set_yticklabels([])
    fig.suptitle("Before any attack: all six detectors separate watermarked images from real photos",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", color=INK)
    fig.text(0.01, 0.005, "One dot per image: 100 watermarked, 200 unwatermarked, 100 real photos per scheme. Filled = "
             "native detector says watermarked; count at right = flagged / total.\nDashed black = native threshold; "
             "dotted orange = calibrated threshold (at most 2 of 200 unwatermarked images above it).",
             fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.06, 0.98, 0.95))
    fig.savefig(out / "fig1_baselines.png", dpi=200)
    plt.close(fig)


def fig_trajectories(rows, calibration, covers, out):
    fig, axes = plt.subplots(2, 3, figsize=(10, 6.2))
    for ax, scheme in zip(axes.flat, ORDER):
        real = rows[(rows.scheme == scheme) & (rows.stage == "baseline") & (rows.kind == "real")]
        f = rows[(rows.scheme == scheme) & (rows.stage == "imprint")]
        for i, c in enumerate(covers):
            tr = f[f.image_id == c].sort_values("step")
            r0 = real[real.image_id == c]
            xs = [0] + list(tr.step)
            ys = [r0.raw_score.iloc[0]] + list(tr.raw_score)
            ds = [bool(r0.native.iloc[0])] + list(tr.native.astype(bool))
            ax.plot(xs, ys, color=SERIES[i], lw=1.1, zorder=2, alpha=0.9)
            for x, y, d in zip(xs, ys, ds):
                ax.scatter(x, y, s=14, marker=MARKERS[i], zorder=3, lw=0.9,
                           facecolors=SERIES[i] if d else "white", edgecolors=SERIES[i])
        threshold_lines(ax, scheme, calibration)
        for b in (50, 100, 150):
            ax.axvline(b, color=GRID, lw=1.2, zorder=0)
        if THRESH[scheme][1] == "below":
            ax.invert_yaxis()
        last = f[f.step == 150]
        k, kc = int(last.native.sum()), int(calibrated(last, scheme, calibration).sum())
        ax.set_title(NAMES[scheme], loc="left", pad=15)
        ax.text(0.0, 1.015, f"at step 150: {k}/10 native, {kc}/10 calibrated", transform=ax.transAxes,
                ha="left", va="bottom", fontsize=7.5, color=INK2)
        ax.set_xlabel("imprint step", fontsize=8)
        ax.set_ylabel(SCORE_LABEL[scheme] + (" (axis flipped)" if THRESH[scheme][1] == "below" else ""), fontsize=8)
        ax.set_xticks([0, 50, 100, 150])
        if scheme == "PRC":
            ax.ticklabel_format(axis="y", style="plain")
            ax.tick_params(axis="y", labelsize=7)
    handles = [plt.Line2D([], [], color=SERIES[i], marker=MARKERS[i], lw=1.1, ms=4, label=c)
               for i, c in enumerate(covers)]
    fig.legend(handles=handles, loc="upper right", ncol=10, frameon=False, fontsize=7,
               bbox_to_anchor=(0.995, 0.955), title="COCO cover", title_fontsize=7)
    fig.suptitle("Fixed-budget imprint forgery: every run goes to 150 steps, whatever the detector says",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", color=INK, y=0.995)
    fig.text(0.01, 0.005, "Step 0 = the untouched photo. Filled marker = native detector says watermarked. Up = toward "
             "detection on every panel.\nDashed black = native threshold; dotted orange = calibrated threshold. "
             "Grey verticals mark the reported budgets (50, 100, 150). Same ten COCO photos for every scheme.",
             fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.055, 1, 0.9))
    fig.savefig(out / "fig2_trajectories.png", dpi=200)
    plt.close(fig)


def fig_cost(rows, calibration, covers, out):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.9), sharey=True)
    ypos = {s: i for i, s in enumerate(ORDER)}
    for scheme in ORDER:
        f = rows[(rows.scheme == scheme) & (rows.stage == "imprint")]
        for i, c in enumerate(covers):
            tr = f[f.image_id == c].sort_values("step")
            hits = tr[tr.native.astype(bool)]
            forged = not hits.empty
            step = int(hits.step.iloc[0]) if forged else 170
            psnr = float(tr[tr.step == 150].psnr.iloc[0])
            y = ypos[scheme] + (i - 4.5) * 0.07
            kw = dict(s=26, marker=MARKERS[i], zorder=3, lw=1.0, edgecolors=SERIES[i],
                      facecolors=SERIES[i] if forged else "white")
            a1.scatter(step, y, **kw)
            a2.scatter(psnr, y, **kw)
        k = int(f[f.step == 150].native.sum())
        a1.text(184, ypos[scheme], f"{k}/10", va="center", color=INK2, fontsize=8)
    a1.set_yticks(range(len(ORDER)), [NAMES[s] for s in ORDER])
    a1.set_ylim(len(ORDER) - 0.5, -0.5)
    a1.set_xlim(0, 195)
    a1.set_xticks([0, 50, 100, 150, 170], ["0", "50", "100", "150", "never"])
    a1.set_xlabel("first step at which the native detector accepted (hollow = never by 150)", fontsize=8)
    a1.set_title("Steps until the forgery is accepted", loc="left")
    a2.set_xlabel("PSNR at step 150 vs the original photo (dB, higher = less visible damage)", fontsize=8)
    a2.set_title("Damage to the photo at the full budget", loc="left")
    for a in (a1, a2):
        a.grid(axis="y", visible=False)
    handles = [plt.Line2D([], [], color=SERIES[i], marker=MARKERS[i], lw=0, ms=5, label=c)
               for i, c in enumerate(covers)]
    fig.legend(handles=handles, loc="lower center", ncol=10, frameon=False, fontsize=7.5, bbox_to_anchor=(0.5, 0.0))
    fig.suptitle("Damage depends on the photo and the budget, not on the scheme being forged",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", color=INK, y=0.985)
    fig.tight_layout(rect=(0, 0.08, 1, 0.93))
    fig.savefig(out / "fig3_cost.png", dpi=200)
    plt.close(fig)


def fig_removal(rows, calibration, out):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.7))
    cols = [("clean", "No attack")] + ATTACKS
    for ax, rule in zip(axes, ["native", "calibrated"]):
        grid = np.zeros((len(ORDER), len(cols)))
        for i, scheme in enumerate(ORDER):
            for j, (attack, _) in enumerate(cols):
                if attack == "clean":
                    v = rows[(rows.scheme == scheme) & (rows.stage == "baseline") & (rows.kind == "watermarked")]
                else:
                    v = rows[(rows.scheme == scheme) & (rows.stage == "removal") & (rows.attack == attack)]
                hit = v.native.astype(bool) if rule == "native" else calibrated(v, scheme, calibration)
                grid[i, j] = hit.sum()
        ax.imshow(grid, cmap="Blues", vmin=0, vmax=130, aspect="auto")
        for i in range(len(ORDER)):
            for j in range(len(cols)):
                n = int(grid[i, j])
                ax.text(j, i, f"{n}", ha="center", va="center", fontsize=9,
                        color="white" if n >= 70 else INK, fontweight="bold" if n <= 10 else "normal")
        ax.set_xticks(range(len(cols)), [c[1] for c in cols], fontsize=8)
        ax.set_yticks(range(len(ORDER)), [NAMES[s] for s in ORDER] if rule == "native" else [])
        ax.axvline(0.5, color="white", lw=3)
        ax.grid(False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(length=0)
        ax.set_title("Native detector" if rule == "native" else "Calibrated test (PRC: score-only)", loc="left")
    fig.suptitle("Removal: crop erases five of six watermarks; purification defeats three native detectors",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", color=INK, y=0.985)
    fig.text(0.01, 0.01, "Each cell = watermarked images still detected, out of the same 100 per scheme (initial "
             "misses included). Bold = 10 or fewer. 'No attack' is the clean detection rate for reference.",
             fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.06, 1, 0.93))
    fig.savefig(out / "fig5_removal.png", dpi=200)
    plt.close(fig)


def verdict(row, scheme, calibration):
    nat = "yes" if bool(row.native) else "no"
    cal = "yes" if row.score > calibration[scheme]["threshold"] else "no"
    return f"native {nat} · calibrated {cal}"


def fig_examples(rows, calibration, images: Path, out):
    covers = rows[(rows.stage == "imprint") & (rows.step == 150)]
    tr_miss = covers[(covers.scheme == "TR") & ~covers.native.astype(bool)].image_id.tolist()
    cover = tr_miss[0] if tr_miss else covers.image_id.iloc[0]
    fig, axes = plt.subplots(2, 5, figsize=(10, 6.3), layout="constrained")
    for r, scheme in enumerate(["GS", "TR"]):
        f = rows[(rows.scheme == scheme) & (rows.stage == "imprint") & (rows.image_id == cover)]
        panels = [(images / "inputs" / f"{cover}.png", "Real photo (cover)", ""),
                  (images / "images" / scheme / "references" / f"{cover}.png", f"{NAMES[scheme]} reference", "")]
        for step in (50, 100, 150):
            row = f[f.step == step].iloc[0]
            panels.append((images / row.artifact, f"Forged, step {step}",
                           f"{verdict(row, scheme, calibration)}\nPSNR {row.psnr:.1f} dB · SSIM {row.ssim:.2f}"))
        for ax, (path, title, note) in zip(axes[r], panels):
            with Image.open(path) as im:
                ax.imshow(im.convert("RGB"))
            ax.set_title(title, fontsize=9.5, loc="left")
            ax.set_xlabel(note, fontsize=8.5, color=INK2)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.grid(False)
    fig.suptitle(f"One photo (COCO {cover}) forged against two schemes at the three budgets",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", color=INK)
    fig.savefig(out / "fig4_examples.png", dpi=170)
    plt.close(fig)

    scheme = "RI"
    base = rows[(rows.scheme == scheme) & (rows.stage == "baseline") & (rows.kind == "watermarked")].iloc[0]
    fig, axes = plt.subplots(1, 5, figsize=(10, 3.0))
    panels = [(images / base.artifact, "Watermarked (no attack)", verdict(base, scheme, calibration))]
    for attack, label in ATTACKS:
        row = rows[(rows.scheme == scheme) & (rows.stage == "removal") & (rows.attack == attack)
                   & (rows.image_id == base.image_id)].iloc[0]
        panels.append((images / row.artifact, label, verdict(row, scheme, calibration)))
    for ax, (path, title, note) in zip(axes, panels):
        with Image.open(path) as im:
            ax.imshow(im.convert("RGB"))
        ax.set_title(title, fontsize=9.5, loc="left")
        ax.set_xlabel(note, fontsize=8.5, color=INK2)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)
    fig.suptitle(f"The four removal attacks on one {NAMES[scheme]} image",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(out / "fig6_removal_examples.png", dpi=170)
    plt.close(fig)


def fig_pipeline(out):
    """Benchmark as run in Check-in 3: F1 sets inclusion and thresholds, F2 and F3 reuse them."""
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    blue, orange, green, purple = SERIES[0], SERIES[1], SERIES[2], SERIES[5]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 46)
    ax.axis("off")

    def box(x, y, w, h, text, color, fill=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", lw=1.6,
                                    edgecolor=color, facecolor=color + "1a" if fill else "white"))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8.2, color=INK, linespacing=1.35)

    def arrow(a, b, color=INK2, style="-|>", ls="-"):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=11, lw=1.3, color=color, linestyle=ls))

    ax.text(1, 43.5, "F1 · Provider: baselines, inclusion and calibration", color=blue, fontsize=9.5, fontweight="bold")
    box(1, 32, 17, 8, "Prompt + seed\n+ saved key", blue)
    box(23, 32, 19, 8, "SD 2.1-base\n100 watermarked\n200 unwatermarked", blue)
    box(47, 32, 17, 8, "+ 100 real\nCOCO photos", blue)
    box(69, 32, 30, 8, "Detector score + native verdict\ninclusion rule; calibrated threshold\n(at most 2 of 200 unwatermarked)", blue, True)
    arrow((18.6, 36), (22.4, 36)); arrow((42.6, 36), (46.4, 36)); arrow((64.6, 36), (68.4, 36))

    ax.text(1, 27.5, "F2 · Attacker: imprint forgery at fixed budgets", color=orange, fontsize=9.5, fontweight="bold")
    box(1, 16, 17, 8, "Real photo c\n(10 COCO covers)", orange, True)
    box(23, 16, 19, 8, "Optimize latent z so\nInvert(z) ≈ Invert(Encode(r))", orange)
    box(47, 16, 17, 8, "Every 10 steps:\ndecode, detect,\ncheckpoint", orange)
    box(69, 16, 30, 8, "Report steps 50, 100, 150\nnative and calibrated\n(never stops early)", orange, True)
    arrow((18.6, 20), (22.4, 20)); arrow((42.6, 20), (46.4, 20)); arrow((64.6, 20), (68.4, 20))
    arrow((55.5, 15.4), (32.5, 15.4), color=orange, ls="--")
    ax.text(44, 12.0, "Adam step on z, 150 steps", color=orange, fontsize=7.5, ha="center")
    ax.text(32.5, 25.6, "reference r = a watermarked F1-style image", color=MUTED, fontsize=7.2, ha="center")

    ax.text(1, 9.5, "F3 · Removal on the same 100 watermarked images", color=green, fontsize=9.5, fontweight="bold")
    box(1, 0.8, 17, 6.6, "100 watermarked\nimages from F1", green, True)
    box(23, 0.8, 41, 6.6, "JPEG q95 · blur r2 · crop 0.8 + rescale · purification 0.3", green)
    box(69, 0.8, 30, 6.6, "Detect the saved result\nnative and calibrated", green, True)
    arrow((18.6, 4.1), (22.4, 4.1)); arrow((64.6, 4.1), (68.4, 4.1))

    arrow((84, 31.4), (84, 24.6), color=purple, style="-|>")
    ax.text(85, 28, "thresholds", color=purple, fontsize=7.5, va="center")
    fig.suptitle("The Check-in 3 benchmark: one versioned log, two decision rules, three experiments",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out / "fig7_pipeline.png", dpi=200)
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", type=Path, default=Path("results/checkin3/full"))
    parser.add_argument("--images", type=Path, help="run directory that still has inputs/ and images/")
    parser.add_argument("--out", type=Path, default=Path("results/checkin3/full/figures"))
    args = parser.parse_args(argv)
    rows, calibration, covers = load(args.run)
    args.out.mkdir(parents=True, exist_ok=True)
    style()
    fig_baselines(rows, calibration, args.out)
    fig_trajectories(rows, calibration, covers, args.out)
    fig_cost(rows, calibration, covers, args.out)
    fig_removal(rows, calibration, args.out)
    fig_pipeline(args.out)
    if args.images is not None:
        fig_examples(rows, calibration, args.images, args.out)
    print("wrote figures to", args.out)


if __name__ == "__main__":
    main()
