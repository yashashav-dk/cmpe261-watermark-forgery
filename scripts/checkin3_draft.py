"""Render the Check-in 3 draft with explicit pending results and optional live summary."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
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
    text = text.replace("—", "-").replace("–", "-").replace("‑", "-")
    pages, current = [], []

    def height(block):
        lines, level = block
        return len(lines) * (0.026 if level == 1 else 0.023 if level else 0.0185) + 0.014

    # Keep references distinct and keep section headings with their first paragraph.
    blocks = [part for block in text.split("\n\n") for part in re.split(r"\n(?=\[\d+\])", block)]
    for block in blocks:
        block = " ".join(block.split())
        if not block:
            continue
        level = len(block) - len(block.lstrip("#")) if block.startswith("#") else 0
        lines = textwrap.wrap(
            block.lstrip("# "), width=82 if level else 96,
            break_long_words=False, break_on_hyphens=False,
        )
        item = (lines, level)
        if sum(height(b) for b in current) + height(item) > 0.81 and current:
            carry = [current.pop()] if current[-1][1] else []
            if current:
                pages.append(current)
            current = carry
        while height(item) > 0.81 - sum(height(b) for b in current):
            available = 0.81 - sum(height(b) for b in current) - 0.014
            line_height = 0.026 if level == 1 else 0.023 if level else 0.0185
            count = int(available / line_height)
            if count:
                current.append((item[0][:count], level))
                item = (item[0][count:], level)
            pages.append(current)
            current = []
        current.append(item)
    if current:
        pages.append(current)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(
        out,
        metadata={
            "Title": "Group 6 — Check-in 3 draft",
            "Author": "Group 6",
            "Subject": "Core watermark benchmark: methods, GPU pilot, and pending full results",
            "Creator": "Group 6 report renderer",
        },
    ) as pdf:
        for n, blocks in enumerate(pages, 1):
            fig = plt.figure(figsize=(8.5, 11), facecolor="white")
            y = 0.93
            for lines, level in blocks:
                for line in lines:
                    fig.text(
                        0.085,
                        y,
                        line,
                        fontsize=15 if level == 1 else 11.5 if level else 10,
                        weight="bold" if level else "normal",
                        family="DejaVu Sans",
                        va="top",
                    )
                    y -= 0.026 if level == 1 else 0.023 if level else 0.0185
                y -= 0.014
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
