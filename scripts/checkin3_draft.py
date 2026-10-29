"""Render the Check-in 3 report, its tables and saved figures, with an optional measurement appendix."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

TABLE = -1
CAPTIONS = {
    "baseline": "F1 baseline acceptance: native and calibrated rates with Wilson 95% intervals.",
    "imprint": "F2 fixed-budget forgery acceptance at steps 50, 100, and 150 (10 covers per scheme).",
    "removal": "F3 watermark retention after each removal attack (100 watermarked images per scheme).",
}


def table_lines(block):
    """Markdown table rows as aligned monospace lines, without the separator row."""
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in block.splitlines()
    ]
    rows = [r for r in rows if not all(re.fullmatch(r":?-{3,}:?", c) for c in r)]
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    lines = ["  ".join(c.ljust(w) for c, w in zip(r, widths)) for r in rows]
    return lines[:1] + ["-" * len(lines[0])] + lines[1:]


def line_height(level):
    if level == TABLE:
        return 0.0165
    return 0.026 if level == 1 else 0.023 if level else 0.0185


def appendix(run):
    from wmforge.checkin3_report import report

    table = report(run)
    complete = sum(c["complete"] for c in table)
    text = "## Appendix: per-cell measurements\n\n"
    text += f"{complete}/{len(table)} required cells complete."
    text += " Incomplete cells are provisional.\n\n" if complete < len(table) else "\n\n"
    for c in table:
        what = c["kind"] if c["stage"] == "imprint" else c["attack"] or c["kind"]
        label = f"{c['scheme']} {c['stage']} {what}" + (f" step {c['step']}" if c["step"] else "")
        detail = f"{label}: {c['observed_n']}/{c['expected_n']} observed/required"
        if "native_rate" in c:
            lo, hi = c["native_wilson95"]
            detail += f"; native {c['native_rate']:.1%} [{lo:.1%}, {hi:.1%}]"
        if "calibrated_rate" in c:
            lo, hi = c["calibrated_wilson95"]
            detail += f"; {c['calibrated_label']} {c['calibrated_rate']:.1%} [{lo:.1%}, {hi:.1%}]"
        text += detail + ".\n\n"
        for metric in ["psnr", "ssim", "lpips"]:
            if metric in c:
                low, high = c[metric]["bootstrap95"]
                name = "PSNR (dB)" if metric == "psnr" else metric.upper()
                text += (
                    f"{label} {name}: mean {c[metric]['mean']:.3f}; bootstrap 95% "
                    f"[{low:.3f}, {high:.3f}]; finite n={c[metric]['n_finite']}.\n\n"
                )
    return text


def paginate(text):
    text = text.replace("—", "-").replace("–", "-").replace("‑", "-")
    pages, current = [], []

    def height(block):
        lines, level = block
        return len(lines) * line_height(level) + 0.014

    def keeps_with_next(block):
        lines, level = block
        return level > 0 or lines[0].startswith("Table ")

    # Keep references distinct; keep headings and table captions with the next block.
    blocks = [part for block in text.split("\n\n") for part in re.split(r"\n(?=\[\d+\])", block)]
    for block in blocks:
        if block.strip().startswith("|"):
            item = (table_lines(block.strip()), TABLE)
            level = TABLE
        else:
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
            carry = [current.pop()] if keeps_with_next(current[-1]) else []
            if current:
                pages.append(current)
            current = carry
        while height(item) > 0.81 - sum(height(b) for b in current):
            available = 0.81 - sum(height(b) for b in current) - 0.014
            count = int(available / line_height(level))
            if count:
                current.append((item[0][:count], level))
                item = (item[0][count:], level)
            pages.append(current)
            current = []
        current.append(item)
    if current:
        pages.append(current)
    return pages


def render(source, out, run=None, figures=None):
    """Text pages, then one page per saved figure, then the optional appendix."""
    pages = paginate(Path(source).read_text())
    appendix_pages = paginate(appendix(run)) if run is not None else []
    figure_paths = []
    if figures is not None:
        figure_paths = [
            Path(figures) / f"{stage}.png"
            for stage in CAPTIONS
            if (Path(figures) / f"{stage}.png").exists()
        ]
    total = len(pages) + len(figure_paths) + len(appendix_pages)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(
        out,
        metadata={
            "Title": "Group 6 — Check-in 3 draft",
            "Author": "Group 6",
            "Subject": "Core watermark benchmark: baselines, fixed-budget forgery, and removal",
            "Creator": "Group 6 report renderer",
        },
    ) as pdf:
        n = 0
        for blocks in pages:
            n += 1
            text_page(pdf, blocks, n, total)
        for figure, path in enumerate(figure_paths, 1):
            n += 1
            fig = plt.figure(figsize=(8.5, 11), facecolor="white")
            image = plt.imread(path)
            # Full text width at the image's own aspect ratio, caption directly below.
            height = 0.92 * 8.5 / 11 * image.shape[0] / image.shape[1]
            ax = fig.add_axes([0.04, 0.92 - height, 0.92, height])
            ax.imshow(image)
            ax.axis("off")
            fig.text(0.085, 0.9 - height, f"Figure {figure}. {CAPTIONS[path.stem]}", fontsize=10, va="top")
            footer(fig, n, total)
            pdf.savefig(fig)
            plt.close(fig)
        for blocks in appendix_pages:
            n += 1
            text_page(pdf, blocks, n, total)
    return total


def text_page(pdf, blocks, n, total):
    fig = plt.figure(figsize=(8.5, 11), facecolor="white")
    y = 0.93
    for lines, level in blocks:
        for line in lines:
            fig.text(
                0.085,
                y,
                line,
                fontsize=8 if level == TABLE else 15 if level == 1 else 11.5 if level else 10,
                weight="bold" if level > 0 else "normal",
                family="DejaVu Sans Mono" if level == TABLE else "DejaVu Sans",
                va="top",
            )
            y -= line_height(level)
        y -= 0.014
    footer(fig, n, total)
    pdf.savefig(fig)
    plt.close(fig)


def footer(fig, n, total):
    fig.text(0.085, 0.045, "CMPE 261 | Group 6 | Check-in 3 draft report", fontsize=8, color="#555555")
    fig.text(0.915, 0.045, f"{n}/{total}", fontsize=8, ha="right", color="#555555")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="docs/checkin-3.md")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--figures", type=Path, help="directory with baseline/imprint/removal.png; defaults to RUN/figures")
    args = parser.parse_args()
    figures = args.figures or (args.run / "figures" if args.run else None)
    print(f"{render(args.source, args.out, args.run, figures)} pages: {args.out}")


if __name__ == "__main__":
    main()
