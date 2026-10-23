"""Completeness-aware Check-in 3 rates and quality intervals, without pooling history."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from wmforge import benchmark as b, metrics
from wmforge.harness import SCHEMES


def summarize(rows, calibrations):
    result = []
    for scheme in SCHEMES:
        calibration = calibrations.get(scheme)
        cells = [
            ("baseline", kind, "", 0, n)
            for kind, n in [("watermarked", 100), ("unwatermarked", 200), ("real", 100)]
        ]
        if calibration is None or calibration["included"]:
            cells += [
                ("imprint", "forged", "imprint", step, 10) for step in [50, 100, 150]
            ]
            cells += [
                ("removal", "watermarked", attack, 0, 100) for attack in b.ATTACKS
            ]
        for stage, kind, attack, step, expected in cells:
            found = [
                r
                for r in rows
                if (r["scheme"], r["stage"], r["kind"], r["attack"], r["step"])
                == (scheme, stage, kind, attack, step)
            ]
            n = len(found)
            cell = dict(
                scheme=scheme,
                stage=stage,
                kind=kind,
                attack=attack,
                step=step,
                expected_n=expected,
                observed_n=n,
                complete=n == expected,
                included=None if calibration is None else calibration["included"],
            )
            if n:
                successes = sum(r["native"] for r in found)
                cell.update(
                    native_successes=successes,
                    native_rate=successes / n,
                    native_wilson95=metrics.wilson_interval(successes, n),
                )
                if calibration:
                    successes = sum(
                        r["score"] > calibration["threshold"] for r in found
                    )
                    cell.update(
                        calibrated_successes=successes,
                        calibrated_rate=successes / n,
                        calibrated_wilson95=metrics.wilson_interval(successes, n),
                        calibrated_label="PRC score-only calibrated test"
                        if scheme == "PRC"
                        else "calibrated score test",
                    )
                for name in ["psnr", "ssim", "lpips"]:
                    values = [
                        float(r[name])
                        for r in found
                        if name in r and np.isfinite(float(r[name]))
                    ]
                    if values:
                        cell[name] = dict(
                            mean=float(np.mean(values)),
                            bootstrap95=metrics.bootstrap_ci(
                                values, n_resamples=10000, seed=261
                            ),
                            n_finite=len(values),
                        )
            result.append(cell)
    return result


def report(root):
    root = Path(root)
    log = b.BenchmarkLog(root / "measurements-v2.json")
    for row in log.rows:
        b.verify_artifact(root, row)
    calibrations = {
        scheme: json.loads((root / f"{scheme}-calibration.json").read_text())
        for scheme in SCHEMES
        if (root / f"{scheme}-calibration.json").exists()
    }
    from wmforge.checkin3 import scheme_calibration

    for scheme, stored in calibrations.items():
        if stored != scheme_calibration(log, scheme):
            raise ValueError(f"{scheme}: calibration differs from its saved baseline")
    table = summarize(log.rows, calibrations)
    b.atomic_bytes(
        root / "summary-v2.json", json.dumps(table, indent=2, allow_nan=False).encode()
    )
    lines = [
        "# Check-in 3 progress and measurements",
        "",
        "Only exact step-50, step-100, and step-150 images enter forgery results. Rates below use observed items; incomplete cells are provisional and never substitute for the required denominator.",
        "",
        "Calibration is an empirical operating point on 200 generated negatives (0.5-percentage-point resolution). It is not independent evidence of population FPR. PRC score-only decisions are separate from native decoder verdicts.",
        "",
        "| Scheme | Stage | Kind / attack / step | Observed / required | Native rate [Wilson 95%] | Calibrated rate [Wilson 95%] |",
        "|---|---|---|---|---|---|",
    ]

    def rate(cell, prefix):
        if prefix + "_rate" not in cell:
            return "pending"
        low, high = cell[prefix + "_wilson95"]
        return f"{cell[prefix + '_rate']:.1%} [{low:.1%}, {high:.1%}]"

    for cell in table:
        descriptor = cell["attack"] or cell["kind"]
        if cell["step"]:
            descriptor += f" / {cell['step']}"
        status = "" if cell["complete"] else " (incomplete)"
        lines.append(
            f"| {cell['scheme']} | {cell['stage']} | {descriptor} | {cell['observed_n']}/{cell['expected_n']}{status} | {rate(cell, 'native')} | {rate(cell, 'calibrated')} |"
        )
    for scheme, calibration in calibrations.items():
        if not calibration["included"]:
            lines.extend(
                [
                    "",
                    f"{scheme}: excluded by the native clean TPR / generated FPR inclusion rule.",
                ]
            )
    lines.extend(
        [
            "",
            "Continuous metrics and their 10,000-resample bootstrap intervals are in `summary-v2.json`. Missing or infinite metric values are excluded explicitly through each metric’s `n_finite` count.",
        ]
    )
    b.atomic_bytes(root / "summary-v2.md", "\n".join(lines).encode())
    if log.rows:
        figures(root, table)
    return table


def figures(root, table):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    root = Path(root) / "figures"
    root.mkdir(parents=True, exist_ok=True)
    labels = {
        "baseline": ["watermarked", "unwatermarked", "real"],
        "imprint": ["50", "100", "150"],
        "removal": list(b.ATTACKS),
    }
    titles = {
        "baseline": "Baseline acceptance",
        "imprint": "Fixed-budget forgery acceptance",
        "removal": "Watermark retention after removal",
    }
    for stage in labels:
        fig, axes = plt.subplots(
            2, 3, figsize=(12, 7), sharey=True, layout="constrained"
        )
        for scheme, ax in zip(SCHEMES, axes.flat):
            cells = [c for c in table if c["scheme"] == scheme and c["stage"] == stage]
            ax.set_title(scheme)
            ax.set_ylim(-0.04, 1.12)
            ax.grid(axis="y", alpha=0.2)
            ax.set_xticks(range(len(labels[stage])), labels[stage], rotation=15)
            if not cells:
                ax.text(
                    0.5,
                    0.5,
                    "Excluded by native baseline rule",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=9,
                )
                continue
            any_observations = False
            for prefix, offset, color in [
                ("native", -0.09, "#185f9c"),
                ("calibrated", 0.09, "#b3531d"),
            ]:
                for i, cell in enumerate(cells):
                    if prefix + "_rate" not in cell:
                        continue
                    any_observations = True
                    rate = cell[prefix + "_rate"]
                    low, high = cell[prefix + "_wilson95"]
                    label = prefix if i == 0 else None
                    ax.errorbar(
                        i + offset,
                        rate,
                        yerr=[[max(0, rate - low)], [max(0, high - rate)]],
                        fmt="o" if prefix == "native" else "s",
                        color=color,
                        capsize=3,
                        markersize=5,
                        label=label,
                    )
            if not any_observations:
                ax.text(
                    0.5,
                    0.5,
                    "Pending",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                )
            ax.text(
                0.02,
                0.98,
                "n=" + ", ".join(f"{c['observed_n']}/{c['expected_n']}" for c in cells),
                transform=ax.transAxes,
                va="top",
                fontsize=8,
            )
            if any(c["observed_n"] for c in cells) and not all(
                c["complete"] for c in cells
            ):
                ax.text(
                    0.98,
                    0.07,
                    "PROVISIONAL",
                    transform=ax.transAxes,
                    ha="right",
                    fontsize=8,
                )
        axes[0, 0].set_ylabel("Acceptance rate; Wilson 95% interval")
        axes[1, 0].set_ylabel("Acceptance rate; Wilson 95% interval")
        handles, legend_labels = [], []
        for ax in axes.flat:
            h, labs = ax.get_legend_handles_labels()
            for handle, label in zip(h, labs):
                if label not in legend_labels:
                    handles.append(handle)
                    legend_labels.append(label)
        if handles:
            fig.legend(handles, legend_labels, loc="outside lower center", ncol=2)
        fig.suptitle(titles[stage] + " | calibrated PRC is score-only", fontsize=13)
        fig.savefig(root / (stage + ".png"), dpi=160)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    table = report(args.run)
    print(f"{sum(c['complete'] for c in table)}/{len(table)} required cells complete")


if __name__ == "__main__":
    main()
