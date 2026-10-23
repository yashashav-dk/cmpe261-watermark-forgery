"""Render the Check-in 3 draft with explicit pending results and optional live summary."""

from __future__ import annotations

import argparse
from pathlib import Path
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


def render(source, out, run=None):
    text = Path(source).read_text()
    if run is not None:
        from wmforge.checkin3_report import report

        table = report(run)
        complete = sum(c["complete"] for c in table)
        text += "\n\n## Current measurement appendix\n\n"
        text += f"{complete}/{len(table)} required cells complete. Incomplete cells are provisional.\n\n"
        for c in table:
            label = f"{c['scheme']} {c['stage']} {c['attack'] or c['kind']} step {c['step']}"
            detail = f"{label}: {c['observed_n']}/{c['expected_n']} observed/required"
            if "native_rate" in c:
                lo, hi = c["native_wilson95"]
                detail += f"; native {c['native_rate']:.1%} [{lo:.1%}, {hi:.1%}]"
            if "calibrated_rate" in c:
                lo, hi = c["calibrated_wilson95"]
                detail += f"; {c['calibrated_label']} {c['calibrated_rate']:.1%} [{lo:.1%}, {hi:.1%}]"
            text += detail + ".\n\n"
    pages = []
    current = []
    for block in text.split("\n\n"):
        block = " ".join(block.split())
        if not block:
            continue
        heading = block.startswith("#")
        if block.startswith("##") and current:
            pages.append(current)
            current = []
        lines = textwrap.wrap(
            block.lstrip("# "), width=88 if heading else 99, break_long_words=True
        )
        if sum(len(b[0]) + 1 for b in current) + len(lines) > 47 and current:
            pages.append(current)
            current = []
        current.append((lines, heading))
    if current:
        pages.append(current)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(
        out,
        metadata={
            "Title": "Group 6 — Check-in 3 draft",
            "Author": "Group 6",
            "Subject": "Core watermark benchmark: methods and pending results",
            "Creator": "Group 6 report renderer",
        },
    ) as pdf:
        for n, blocks in enumerate(pages, 1):
            fig = plt.figure(figsize=(8.5, 11), facecolor="white")
            y = 0.93
            for lines, heading in blocks:
                for line in lines:
                    fig.text(
                        0.085,
                        y,
                        line,
                        fontsize=11 if heading else 9.5,
                        weight="bold" if heading else "normal",
                        family="DejaVu Sans",
                        va="top",
                    )
                    y -= 0.0185
                y -= 0.012
            fig.text(
                0.085,
                0.045,
                "CMPE 261 | Group 6 | Draft — measurements pending verification",
                fontsize=8,
                color="#555555",
            )
            fig.text(
                0.915,
                0.045,
                f"{n}/{len(pages)}",
                fontsize=8,
                ha="right",
                color="#555555",
            )
            pdf.savefig(fig)
            plt.close(fig)
    return len(pages)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="docs/checkin-3.md")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--run", type=Path)
    args = parser.parse_args()
    print(f"{render(args.source, args.out, args.run)} pages: {args.out}")


if __name__ == "__main__":
    main()
