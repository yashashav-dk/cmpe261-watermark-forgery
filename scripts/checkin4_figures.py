"""Draw a fresh Check-in 4 figure set from the frozen Check-in 3 measurement log.

These are new plots for the draft report. They recompute from
results/checkin3/full/measurements-v2.json but are saved only under
results/checkin4/figures/ and are labeled as Check-in 4 draft figures.

Usage:
    PYTHONPATH=src python scripts/checkin4_figures.py
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
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ORDER = ["GS", "PRC", "WIND", "RI", "SFW", "TR"]
NAMES = {
    "GS": "Gaussian Shading",
    "PRC": "PRC",
    "WIND": "WIND",
    "RI": "Ring-ID",
    "SFW": "SFW",
    "TR": "Tree-Ring",
}
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
KINDS = [("watermarked", "Watermarked"), ("unwatermarked", "Unwatermarked"), ("real", "Real photos")]

INK, INK2, MUTED, GRID = "#1f1f1e", "#55544f", "#8a8983", "#e6e5e0"
SERIES = [
    "#2a78d6",
    "#eb6834",
    "#1baf7a",
    "#eda100",
    "#e87ba4",
    "#7b5cd6",
    "#14a3b8",
    "#a6761d",
    "#5b6b7a",
    "#c03b3b",
]
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "h", "<", ">"]


def load(run: Path):
    rows = pd.DataFrame(json.loads((run / "measurements-v2.json").read_text())["rows"])
    rows["image_id"] = rows["image_id"].astype(str)
    calibration = {
        s: json.loads((run / f"{s}-calibration.json").read_text()) for s in ORDER
    }
    covers = [
        str(c)
        for c in json.loads((run / "manifest.json").read_text())["image_ids"][:10]
    ]
    return rows, calibration, covers


def raw_threshold(scheme, calibration):
    t = calibration[scheme]["threshold"]
    return -t if THRESH[scheme][1] == "below" else t


def calibrated(rows, scheme, calibration):
    return rows["score"] > calibration[scheme]["threshold"]


def style():
    plt.rcParams.update(
        {
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
        }
    )


def threshold_lines(ax, scheme, calibration, horizontal=True):
    line = ax.axhline if horizontal else ax.axvline
    t, _ = THRESH[scheme]
    if t is not None:
        line(t, color=INK, lw=1, ls=(0, (4, 3)), zorder=1)
    line(raw_threshold(scheme, calibration), color=SERIES[1], lw=1, ls=(0, (1, 2)), zorder=1)


def fig1_baselines(rows, calibration, out):
    fig, axes = plt.subplots(2, 3, figsize=(10, 5.8))
    rng = np.random.default_rng(4)
    for ax, scheme in zip(axes.flat, ORDER):
        g = rows[(rows.scheme == scheme) & (rows.stage == "baseline")]
        for i, (kind, _) in enumerate(KINDS):
            v = g[g.kind == kind]
            y = i + rng.uniform(-0.2, 0.2, len(v))
            det = v.native.to_numpy(bool)
            ax.scatter(
                v.raw_score[~det],
                y[~det],
                s=12,
                facecolors="white",
                edgecolors=SERIES[i],
                lw=1.0,
                zorder=3,
            )
            ax.scatter(v.raw_score[det], y[det], s=12, color=SERIES[i], zorder=3)
            ax.text(
                1.0,
                i,
                f" {det.sum()}/{len(v)}",
                transform=ax.get_yaxis_transform(),
                ha="left",
                va="center",
                color=INK2,
                fontsize=8,
                clip_on=False,
            )
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
    fig.suptitle(
        "Check-in 4 draft · Figure 1. Clean and real-photo baselines (F1)",
        x=0.01,
        ha="left",
        fontsize=11,
        fontweight="bold",
        color=INK,
    )
    fig.text(
        0.01,
        0.005,
        "Recomputed for the Check-in 4 draft from the frozen floor log. One dot per image. "
        "Filled = native detector flagged. Dashed black = native threshold; dotted orange = calibrated.",
        fontsize=7.5,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.06, 0.98, 0.95))
    fig.savefig(out / "fig1_baselines.png", dpi=200)
    plt.close(fig)


def fig2_trajectories(rows, calibration, covers, out):
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
                ax.scatter(
                    x,
                    y,
                    s=14,
                    marker=MARKERS[i],
                    zorder=3,
                    lw=0.9,
                    facecolors=SERIES[i] if d else "white",
                    edgecolors=SERIES[i],
                )
        threshold_lines(ax, scheme, calibration)
        for b in (50, 100, 150):
            ax.axvline(b, color=GRID, lw=1.2, zorder=0)
        if THRESH[scheme][1] == "below":
            ax.invert_yaxis()
        last = f[f.step == 150]
        k, kc = int(last.native.sum()), int(calibrated(last, scheme, calibration).sum())
        ax.set_title(NAMES[scheme], loc="left", pad=15)
        ax.text(
            0.0,
            1.015,
            f"at step 150: {k}/10 native, {kc}/10 calibrated",
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=7.5,
            color=INK2,
        )
        ax.set_xlabel("imprint step", fontsize=8)
        ax.set_ylabel(
            SCORE_LABEL[scheme]
            + (" (axis flipped)" if THRESH[scheme][1] == "below" else ""),
            fontsize=8,
        )
        ax.set_xticks([0, 50, 100, 150])
        if scheme == "PRC":
            ax.ticklabel_format(axis="y", style="plain")
            ax.tick_params(axis="y", labelsize=7)
    handles = [
        plt.Line2D([], [], color=SERIES[i], marker=MARKERS[i], lw=1.1, ms=4, label=c)
        for i, c in enumerate(covers)
    ]
    fig.legend(
        handles=handles,
        loc="upper right",
        ncol=10,
        frameon=False,
        fontsize=7,
        bbox_to_anchor=(0.995, 0.955),
        title="COCO cover",
        title_fontsize=7,
    )
    fig.suptitle(
        "Check-in 4 draft · Figure 2. Fixed-budget imprint trajectories under C1 (F2)",
        x=0.01,
        ha="left",
        fontsize=11,
        fontweight="bold",
        color=INK,
        y=0.995,
    )
    fig.text(
        0.01,
        0.005,
        "New Check-in 4 render of the frozen C1 trajectories. Step 0 = untouched photo. "
        "Filled marker = native accept. Grey lines mark budgets 50, 100 and 150.",
        fontsize=7.5,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.055, 1, 0.9))
    fig.savefig(out / "fig2_trajectories.png", dpi=200)
    plt.close(fig)


def fig3_forgeability(rows, calibration, covers, out):
    medians, accepted, names = [], [], []
    for scheme in ORDER:
        f = rows[(rows.scheme == scheme) & (rows.stage == "imprint")]
        steps = []
        for c in covers:
            tr = f[f.image_id == c].sort_values("step")
            hits = tr[tr.native.astype(bool)]
            if not hits.empty:
                steps.append(int(hits.step.iloc[0]))
        names.append(NAMES[scheme])
        accepted.append(len(steps))
        medians.append(float(np.median(steps)) if steps else np.nan)
    # sort easiest first for the draft figure
    order = np.argsort(medians)
    names = [names[i] for i in order]
    medians = [medians[i] for i in order]
    accepted = [accepted[i] for i in order]
    fig, ax = plt.subplots(figsize=(8.2, 3.8))
    bars = ax.barh(names[::-1], medians[::-1], color="#4c78a8")
    for bar, n in zip(bars, accepted[::-1]):
        ax.text(
            bar.get_width() + 2,
            bar.get_y() + bar.get_height() / 2,
            f"{n}/10 by step 150",
            va="center",
            fontsize=8,
            color=INK2,
        )
    ax.set_xlim(0, 160)
    ax.set_xlabel("Median first native acceptance step")
    ax.set_title("Check-in 4 draft · Figure 3. C1 forgeability order", loc="left")
    fig.tight_layout()
    fig.savefig(out / "fig3_forgeability_order.png", dpi=200)
    plt.close(fig)


def fig4_cover_psnr(rows, covers, out):
    vals = []
    for c in covers:
        group = rows[
            (rows.stage == "imprint") & (rows.step == 150) & (rows.image_id == c)
        ]
        vals.append(float(group.psnr.mean()))
    order = np.argsort(vals)[::-1]
    fig, ax = plt.subplots(figsize=(8.2, 3.8))
    ax.bar(
        [covers[i] for i in order],
        [vals[i] for i in order],
        color="#54a24b",
    )
    ax.set_ylabel("Mean PSNR across six schemes (dB)")
    ax.set_xlabel("COCO cover id")
    ax.tick_params(axis="x", rotation=45)
    ax.set_title(
        "Check-in 4 draft · Figure 4. Perceptual cost at step 150 by cover",
        loc="left",
    )
    fig.tight_layout()
    fig.savefig(out / "fig4_cover_psnr.png", dpi=200)
    plt.close(fig)


def fig5_removal(rows, calibration, out):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.7))
    cols = [("clean", "No attack")] + ATTACKS
    for ax, rule in zip(axes, ["native", "calibrated"]):
        grid = np.zeros((len(ORDER), len(cols)))
        for i, scheme in enumerate(ORDER):
            for j, (attack, _) in enumerate(cols):
                if attack == "clean":
                    v = rows[
                        (rows.scheme == scheme)
                        & (rows.stage == "baseline")
                        & (rows.kind == "watermarked")
                    ]
                else:
                    v = rows[
                        (rows.scheme == scheme)
                        & (rows.stage == "removal")
                        & (rows.attack == attack)
                    ]
                hit = (
                    v.native.astype(bool)
                    if rule == "native"
                    else calibrated(v, scheme, calibration)
                )
                grid[i, j] = hit.sum()
        ax.imshow(grid, cmap="Greens", vmin=0, vmax=130, aspect="auto")
        for i in range(len(ORDER)):
            for j in range(len(cols)):
                n = int(grid[i, j])
                ax.text(
                    j,
                    i,
                    f"{n}",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white" if n >= 70 else INK,
                    fontweight="bold" if n <= 10 else "normal",
                )
        ax.set_xticks(range(len(cols)), [c[1] for c in cols], fontsize=8)
        ax.set_yticks(
            range(len(ORDER)),
            [NAMES[s] for s in ORDER] if rule == "native" else [],
        )
        ax.axvline(0.5, color="white", lw=3)
        ax.grid(False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(length=0)
        ax.set_title(
            "Native detector" if rule == "native" else "Calibrated test",
            loc="left",
        )
    fig.suptitle(
        "Check-in 4 draft · Figure 5. Removal survival under both decision rules (F3)",
        x=0.01,
        ha="left",
        fontsize=11,
        fontweight="bold",
        color=INK,
        y=0.985,
    )
    fig.text(
        0.01,
        0.01,
        "New Check-in 4 heatmap from the frozen removal log. Each cell = still detected out of 100.",
        fontsize=7.5,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 0.93))
    fig.savefig(out / "fig5_removal.png", dpi=200)
    plt.close(fig)


def fig6_purification_gap(rows, calibration, out):
    native, calib, names = [], [], []
    for scheme in ORDER:
        v = rows[
            (rows.scheme == scheme)
            & (rows.stage == "removal")
            & (rows.attack == "purification")
        ]
        names.append(NAMES[scheme])
        native.append(int(v.native.sum()))
        calib.append(int(calibrated(v, scheme, calibration).sum()))
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(8.2, 3.8))
    ax.bar(x - 0.2, native, width=0.4, label="native", color="#4c78a8")
    ax.bar(x + 0.2, calib, width=0.4, label="calibrated", color="#f58518")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=15)
    ax.set_ylabel("Still detected after purification (of 100)")
    ax.legend(frameon=False)
    ax.set_title(
        "Check-in 4 draft · Figure 6. Purification: native verdict vs calibrated score",
        loc="left",
    )
    fig.tight_layout()
    fig.savefig(out / "fig6_purification_gap.png", dpi=200)
    plt.close(fig)


def fig7_disagreement(rows, calibration, out):
    native_only, cal_only, names = [], [], []
    for scheme in ORDER:
        subset = rows[
            (rows.scheme == scheme)
            & (rows.stage == "imprint")
            & (rows.step.isin([50, 100, 150]))
        ]
        n_only = c_only = 0
        for _, row in subset.iterrows():
            n_ok = bool(row.native)
            c_ok = bool(row.score > calibration[scheme]["threshold"])
            if n_ok and not c_ok:
                n_only += 1
            if c_ok and not n_ok:
                c_only += 1
        names.append(NAMES[scheme])
        native_only.append(n_only)
        cal_only.append(c_only)
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(8.2, 3.8))
    ax.bar(x - 0.2, native_only, width=0.4, label="native only", color="#e45756")
    ax.bar(x + 0.2, cal_only, width=0.4, label="calibrated only", color="#72b7b2")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=15)
    ax.set_ylabel("Disagreements at budgets 50 / 100 / 150")
    ax.legend(frameon=False)
    ax.set_title(
        "Check-in 4 draft · Figure 7. Where the two decision rules disagree on forgeries",
        loc="left",
    )
    fig.tight_layout()
    fig.savefig(out / "fig7_threshold_disagreement.png", dpi=200)
    plt.close(fig)


def fig8_pipeline(out):
    blue, orange, green, purple = SERIES[0], SERIES[1], SERIES[2], SERIES[5]
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 52)
    ax.axis("off")

    def box(x, y, w, h, text, color, fill=False):
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.4,rounding_size=1.2",
                lw=1.6,
                edgecolor=color,
                facecolor=color + "1a" if fill else "white",
            )
        )
        ax.text(
            x + w / 2,
            y + h / 2,
            text,
            ha="center",
            va="center",
            fontsize=8.0,
            color=INK,
            linespacing=1.35,
        )

    def arrow(a, b, color=INK2):
        ax.add_patch(
            FancyArrowPatch(
                a, b, arrowstyle="-|>", mutation_scale=11, lw=1.3, color=color
            )
        )

    ax.text(1, 49, "Frozen floor from Check-in 3 (read-only in this draft)", color=blue, fontsize=9.5, fontweight="bold")
    box(1, 38, 17, 8, "Saved keys\ncovers, prompts", blue)
    box(23, 38, 19, 8, "F1 baselines\n+ calibrations", blue)
    box(47, 38, 17, 8, "F2 C1 imprint\nfixed budgets", blue)
    box(69, 38, 30, 8, "F3 removal at toolkit defaults\n5,700-row versioned log", blue, True)
    arrow((18.6, 42), (22.4, 42))
    arrow((42.6, 42), (46.4, 42))
    arrow((64.6, 42), (68.4, 42))

    ax.text(1, 33, "Check-in 4 draft work (new paths only)", color=orange, fontsize=9.5, fontweight="bold")
    box(1, 22, 22, 8, "Offline recompute\nforgeability, gaps,\nquality figures", orange, True)
    box(28, 22, 22, 8, "Draft project report\nsections 1 to 11", orange, True)
    box(55, 22, 20, 8, "C2 runner\nSD 1.5 attacker", orange)
    box(79, 22, 20, 8, "Strength sweeps\ncrop + purification", orange)
    arrow((23.6, 26), (27.4, 26))
    arrow((50.6, 26), (54.4, 26))
    arrow((75.6, 26), (78.4, 26))

    ax.text(1, 16.5, "Inputs reused, outputs isolated", color=green, fontsize=9.5, fontweight="bold")
    box(1, 5.5, 30, 8, "Read: results/checkin3/full/\nkeys, calibrations, log", green, True)
    box(36, 5.5, 30, 8, "Write: results/checkin4/\ndocs/checkin-4*\nnotebooks/04_*", green, True)
    box(71, 5.5, 28, 8, "Final report later:\nC2 rates + sweep curves", green)
    arrow((31.6, 9.5), (35.4, 9.5))
    arrow((66.6, 9.5), (70.4, 9.5))
    arrow((84, 37.4), (84, 30.6), color=purple)
    ax.text(85, 34, "thresholds", color=purple, fontsize=7.5, va="center")

    fig.suptitle(
        "Check-in 4 draft · Figure 8. How this draft continues the frozen floor",
        x=0.01,
        ha="left",
        fontsize=11,
        fontweight="bold",
        color=INK,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out / "fig8_pipeline.png", dpi=200)
    plt.close(fig)


def fig9_budget_bars(rows, calibration, out):
    """Accepted covers at each budget under both rules."""
    budgets = [50, 100, 150]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.0), sharey=True)
    x = np.arange(len(ORDER))
    width = 0.25
    for ax, rule in zip(axes, ["native", "calibrated"]):
        for i, budget in enumerate(budgets):
            vals = []
            for scheme in ORDER:
                v = rows[
                    (rows.scheme == scheme)
                    & (rows.stage == "imprint")
                    & (rows.step == budget)
                ]
                if rule == "native":
                    vals.append(int(v.native.sum()))
                else:
                    vals.append(int(calibrated(v, scheme, calibration).sum()))
            ax.bar(x + (i - 1) * width, vals, width=width, label=f"step {budget}", color=SERIES[i])
        ax.set_xticks(x, [NAMES[s] for s in ORDER], rotation=20, ha="right")
        ax.set_ylim(0, 10.8)
        ax.set_title("Native" if rule == "native" else "Calibrated", loc="left")
        ax.set_ylabel("Accepted covers out of 10")
        ax.legend(frameon=False, fontsize=8)
    fig.suptitle(
        "Check-in 4 draft · Figure 9. Acceptance by budget under both rules",
        x=0.01,
        ha="left",
        fontsize=11,
        fontweight="bold",
        color=INK,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out / "fig9_budget_acceptance.png", dpi=200)
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=Path("results/checkin3/full"))
    parser.add_argument("--out", type=Path, default=Path("results/checkin4/figures"))
    args = parser.parse_args(argv)
    rows, calibration, covers = load(args.run)
    args.out.mkdir(parents=True, exist_ok=True)
    style()
    fig1_baselines(rows, calibration, args.out)
    fig2_trajectories(rows, calibration, covers, args.out)
    fig3_forgeability(rows, calibration, covers, args.out)
    fig4_cover_psnr(rows, covers, args.out)
    fig5_removal(rows, calibration, args.out)
    fig6_purification_gap(rows, calibration, args.out)
    fig7_disagreement(rows, calibration, args.out)
    fig8_pipeline(args.out)
    fig9_budget_bars(rows, calibration, args.out)
    # remove old A/B/C/D names if present so the package only ships the new set
    for old in (
        "figA_forgeability_order.png",
        "figB_threshold_disagreement.png",
        "figC_purification_gap.png",
        "figD_cover_psnr.png",
    ):
        path = args.out / old
        if path.exists():
            path.unlink()
    print("wrote Check-in 4 figures to", args.out)


if __name__ == "__main__":
    main()
