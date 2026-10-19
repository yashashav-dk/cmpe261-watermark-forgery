"""Draw the Check-in 2 figures from the committed run logs. No GPU needed.

Usage:
    python scripts/checkin2_figures.py results/checkin2/runs.csv results/checkin1/runs.csv results/tr150/runs.csv results/checkin2/figures
    python scripts/checkin2_figures.py [--root ROOT] [--out OUT]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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

INK, INK2, MUTED, GRID = "#1f1f1e", "#55544f", "#8a8983", "#e6e5e0"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
MARKERS = ["o", "s", "^", "D", "v"]


def load_all(root: Path) -> pd.DataFrame:
    try:
        from wmforge import report
        frames = [(scheme, report.load(root / run / "runs.csv"), stages) for scheme, run, stages in SOURCES]
        return report.combine_runs(frames)
    except ImportError:
        # Fallback if wmforge is not installed in current environment
        ck1 = pd.read_csv(root / "results/checkin1/runs.csv")
        tr150 = pd.read_csv(root / "results/tr150/runs.csv")
        new = pd.read_csv(root / "results/checkin2/runs.csv")
        parts = []
        for scheme, run, stages in SOURCES:
            df = ck1 if run == "results/checkin1" else (tr150 if run == "results/tr150" else new)
            sub = df[df.scheme == scheme]
            if stages:
                sub = sub[sub.stage.isin(stages)]
            parts.append(sub)
        return pd.concat(parts, ignore_index=True)


def stop_points(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (scheme, cover): step and PSNR where the run stopped, and whether it was forged."""
    rows = []
    covers = sorted(df[(df.stage == "imprint") & (df.kind == "forged")].image_id.astype(str).unique(), key=int)
    for scheme in ORDER:
        f = df[(df.scheme == scheme) & (df.stage == "imprint") & (df.kind == "forged")]
        for c in covers:
            tr = f[f.image_id.astype(str) == c].sort_values("step")
            if tr.empty:
                continue
            hits = tr[tr.is_watermarked == 1]
            stop = hits.iloc[0] if not hits.empty else tr.iloc[-1]
            rows.append({
                "scheme": scheme,
                "cover": c,
                "step": int(stop.step),
                "psnr": float(stop.psnr),
                "forged": bool(not hits.empty),
            })
    return pd.DataFrame(rows)


def threshold_line(ax, scheme, horizontal=True):
    t, side = THRESH[scheme]
    if t is None:
        return
    (ax.axhline if horizontal else ax.axvline)(t, color=INK, lw=1, ls=(0, (4, 3)), zorder=1)


def generate_figures(new: pd.DataFrame, ck1: pd.DataFrame, tr150: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    out_dir.mkdir(parents=True, exist_ok=True)

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

    def logs_for(scheme):
        if scheme in ("GS",):
            return ck1, ck1
        if scheme == "TR":
            return ck1, tr150
        return new, new

    # Figure 1: clean and real-photo baselines
    fig, axes = plt.subplots(2, 3, figsize=(10, 5.6))
    rows = [("watermarked", "Watermarked"), ("unwatermarked", "Unwatermarked"), ("real", "Real photos")]
    rng = np.random.default_rng(0)
    for ax, scheme in zip(axes.flat, ORDER):
        base, _ = logs_for(scheme)
        g = base[(base.scheme == scheme) & (base.stage.isin(["clean", "real"]))]
        for i, (kind, label) in enumerate(rows):
            v = g[g.kind == kind]
            y = i + rng.uniform(-0.18, 0.18, len(v))
            det = v.is_watermarked == 1
            ax.scatter(v.raw_score[~det], y[~det], s=16, facecolors="white", edgecolors=SERIES[i], lw=1.1, zorder=3)
            ax.scatter(v.raw_score[det], y[det], s=16, color=SERIES[i], zorder=3)
            k, n = int(det.sum()), len(v)
            ax.text(1.0, i, f"{k}/{n}", transform=ax.get_yaxis_transform(), ha="left", va="center",
                    color=INK2, fontsize=8, clip_on=False)
        threshold_line(ax, scheme, horizontal=False)
        ax.set_yticks(range(3), [r[1] for r in rows])
        ax.set_ylim(2.6, -0.6)
        ax.grid(axis="y", visible=False)
        t, side = THRESH[scheme]
        sub = f"flagged if {side} {t:g}" if t is not None else "verdict only (direction unverified)"
        ax.set_title(f"{NAMES[scheme]}", loc="left")
        ax.set_xlabel(f"{SCORE_LABEL[scheme]} · {sub}", fontsize=8)
        if scheme == "PRC":
            ax.ticklabel_format(axis="x", style="plain")
            ax.tick_params(axis="x", labelsize=7)
    for ax in axes[:, 1:].flat:
        ax.set_yticklabels([])
    fig.suptitle("Detectors before any attack: every scheme separates watermarked images from real photos",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", color=INK)
    fig.text(0.01, 0.005, "Filled = detector says watermarked; hollow = not. Count at right = flagged / total. "
             "Dashed line = decision threshold.\nGS and TR from Check-in 1; PRC, WIND, RI, SFW from Check-in 2. "
             "50 images per row.", fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.05, 0.98, 0.95))
    fig.savefig(out_dir / "fig1_baselines.png", dpi=200)
    plt.close(fig)

    # Figure 2: trajectories
    covers = sorted(new[(new.stage == "imprint")].image_id.astype(str).unique(), key=int)
    color_of = {c: SERIES[i] for i, c in enumerate(covers)}
    marker_of = {c: MARKERS[i] for i, c in enumerate(covers)}

    fig, axes = plt.subplots(2, 3, figsize=(10, 6))
    for ax, scheme in zip(axes.flat, ORDER):
        base, imp = logs_for(scheme)
        real = base[(base.scheme == scheme) & (base.stage == "real")]
        f = imp[(imp.scheme == scheme) & (imp.stage == "imprint") & (imp.kind == "forged")]
        for c in covers:
            tr = f[f.image_id.astype(str) == c].sort_values("step")
            r0 = real[real.image_id.astype(str) == c]
            xs, ys, ds = list(tr.step), list(tr.raw_score), list(tr.is_watermarked == 1)
            if len(r0):
                xs, ys, ds = [0] + xs, [r0.raw_score.iloc[0]] + ys, [bool(r0.is_watermarked.iloc[0] == 1)] + ds
            ax.plot(xs, ys, color=color_of[c], lw=1.6, zorder=2)
            for x, y, d in zip(xs, ys, ds):
                ax.scatter(x, y, s=26, marker=marker_of[c], zorder=3,
                           facecolors=color_of[c] if d else "white", edgecolors=color_of[c], lw=1.2)
        threshold_line(ax, scheme)
        t, side = THRESH[scheme]
        if t is not None:
            ax.text(1.0, t, f" {t:g}", transform=ax.get_yaxis_transform(), color=INK, fontsize=7.5, va="center")
        if THRESH[scheme][1] == "below":
            ax.invert_yaxis()
        forged = imp[(imp.scheme == scheme) & (imp.stage == "imprint") & (imp.kind == "done")]
        k = int((forged.is_watermarked == 1).sum())
        cap = int(f.step.max()) if scheme != "TR" else 150
        ax.set_title(f"{NAMES[scheme]}  ·  {k}/{len(forged)} forged", loc="left")
        ax.set_xlabel("imprint step", fontsize=8)
        ax.set_ylabel(SCORE_LABEL[scheme] + (" (axis flipped)" if THRESH[scheme][1] == "below" else ""), fontsize=8)
        if scheme == "PRC":
            ax.text(0.02, 0.97, "no fixed threshold; verdict per marker", transform=ax.transAxes,
                    fontsize=7, color=MUTED, va="top")
            ax.ticklabel_format(axis="y", style="plain")
            ax.tick_params(axis="y", labelsize=7)
        ax.set_xlim(-5, max(cap, f.step.max()) + 8)

    handles = [plt.Line2D([], [], color=color_of[c], marker=marker_of[c], lw=1.6, ms=5, label=f"COCO {c}")
               for c in covers]
    fig.legend(handles=handles, loc="upper right", ncol=5, frameon=False, fontsize=8, bbox_to_anchor=(0.99, 0.965))
    fig.suptitle("Imprint forgery: all 30 attacks moved a real photo toward the watermark; 29 crossed the threshold",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", color=INK, y=0.995)
    fig.text(0.01, 0.005, "Step 0 = untouched real photo. Filled marker = detector says watermarked; the run stops at the "
             "first detection. Up = toward detection on every panel. Same five COCO photos for every scheme. "
             "GS and TR from Check-in 1 (TR from the 150-step rerun).", fontsize=7.5, color=MUTED, wrap=True)
    fig.tight_layout(rect=(0, 0.035, 1, 0.93))
    fig.savefig(out_dir / "fig2_trajectories.png", dpi=200)
    plt.close(fig)

    # Figure 3: cost of forgery
    rows3 = []
    for scheme in ORDER:
        _, imp = logs_for(scheme)
        f = imp[(imp.scheme == scheme) & (imp.stage == "imprint") & (imp.kind == "forged")]
        for c in covers:
            tr = f[f.image_id.astype(str) == c].sort_values("step")
            if not len(tr):
                continue
            last = tr.iloc[-1]
            rows3.append(dict(scheme=scheme, cover=c, step=int(last.step), psnr=float(last.psnr),
                              forged=bool(last.is_watermarked == 1)))
    r3 = pd.DataFrame(rows3)
    r3.to_csv(out_dir / "forgery_per_cover.csv", index=False)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    ypos = {s: i for i, s in enumerate(ORDER)}
    for _, r in r3.iterrows():
        y = ypos[r.scheme] + (covers.index(r.cover) - 2) * 0.11
        kw = dict(s=34, marker=marker_of[r.cover], zorder=3, lw=1.2, edgecolors=color_of[r.cover],
                  facecolors=color_of[r.cover] if r.forged else "white")
        a1.scatter(r.step, y, **kw)
        a2.scatter(r.psnr, y, **kw)
    for s in ORDER:
        g = r3[r3.scheme == s]
        a1.text(158, ypos[s], f"{int(g.forged.sum())}/{len(g)}", va="center", color=INK2, fontsize=8)
    a1.set_yticks(range(len(ORDER)), [NAMES[s] for s in ORDER])
    a1.set_ylim(len(ORDER) - 0.5, -0.5)
    a1.set_xlim(0, 168)
    a1.set_xlabel("imprint steps until detected (hollow = not detected by step 150)", fontsize=8)
    a1.set_title("Steps to forge", loc="left")
    a2.axvline(25, color=MUTED, lw=0.8, ls=(0, (2, 3)))
    a2.text(25, -0.75, " ~25 dB", color=MUTED, fontsize=7.5, va="bottom")
    a2.set_xlabel("PSNR of the forged photo vs the original (dB, higher = less visible damage)", fontsize=8)
    a2.set_title("Damage to the photo", loc="left")
    for a in (a1, a2):
        a.grid(axis="y", visible=False)
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, fontsize=8, bbox_to_anchor=(0.5, 0.0))
    fig.suptitle("Wider detector margins slow forgery down but do not stop it",
                 x=0.01, ha="left", fontsize=11, fontweight="bold", color=INK, y=0.985)
    fig.tight_layout(rect=(0, 0.07, 1, 0.93))
    fig.savefig(out_dir / "fig3_cost.png", dpi=200)
    plt.close(fig)

    return r3


def main(argv=None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) == 4 and not argv[0].startswith("-"):
        new_path = Path(argv[0])
        ck1_path = Path(argv[1])
        tr150_path = Path(argv[2])
        out_dir = Path(argv[3])
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("pos_args", nargs="*", help="Optional positional args: NEW CK1 TR150 OUT")
        parser.add_argument("--root", default=".", help="repository root holding results/")
        parser.add_argument("--out", default="results/checkin2/figures", help="output directory")
        parsed = parser.parse_args(argv)
        if len(parsed.pos_args) == 4:
            new_path, ck1_path, tr150_path, out_dir = [Path(p) for p in parsed.pos_args]
        else:
            root = Path(parsed.root)
            new_path = root / "results/checkin2/runs.csv"
            ck1_path = root / "results/checkin1/runs.csv"
            tr150_path = root / "results/tr150/runs.csv"
            out_dir = Path(parsed.out)

    new = pd.read_csv(new_path)
    ck1 = pd.read_csv(ck1_path)
    tr150 = pd.read_csv(tr150_path)
    r3 = generate_figures(new, ck1, tr150, out_dir)
    print(r3.groupby("scheme").agg(forged=("forged", "sum"), n=("forged", "size"),
                                   med_step=("step", "median"), med_psnr=("psnr", "median")).loc[ORDER])
    print("wrote figures to", out_dir)


if __name__ == "__main__":
    main()
