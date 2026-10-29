"""Build the Check-in 3 PDF: docs/checkin-3.md -> styled HTML -> headless Chrome PDF.

Usage:
    python scripts/checkin3_pdf.py
    python scripts/checkin3_pdf.py --source docs/checkin-3.md --summary results/checkin3/full/summary-v2.json \
        --out docs/Group6_CMPE261_CheckIn_3.pdf

Needs the `markdown` package and Google Chrome (or Chromium). The appendix is generated
from summary-v2.json, so every interval in it comes straight from the measurement log.
"""
from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import markdown

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome",
    "chromium",
    "chromium-browser",
]
NAMES = {"GS": "Gaussian Shading", "PRC": "PRC", "WIND": "WIND", "RI": "Ring-ID", "SFW": "SFW", "TR": "Tree-Ring"}
ORDER = ["GS", "PRC", "WIND", "RI", "SFW", "TR"]

CSS = """
@page { size: Letter; margin: 0.7in 0.75in 0.75in;
        @bottom-center { content: counter(page); font: 9pt -apple-system, "Helvetica Neue", Arial, sans-serif; color: #55544f; } }
body { font-family: -apple-system, "Helvetica Neue", "Segoe UI", Arial, sans-serif; font-size: 10pt;
       line-height: 1.45; color: #1f1f1e; }
h1 { font-size: 22pt; margin: 0 0 2pt; }
p.subtitle { font-size: 11.5pt; font-weight: 700; margin: 0 0 6pt; }
h2 { font-size: 14pt; margin: 18pt 0 6pt; break-after: avoid; }
h3 { font-size: 11.5pt; margin: 14pt 0 4pt; break-after: avoid; }
p { margin: 0 0 7pt; }
a { color: #2a78d6; text-decoration: none; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0 6pt; font-size: 8.6pt; }
th, td { border: 1px solid #d9d8d2; padding: 3pt 5pt; vertical-align: top; text-align: left; }
th { background: #f3f2ee; font-weight: 700; }
tr { break-inside: avoid; }
code { font-family: Menlo, Consolas, monospace; font-size: 8.4pt; background: #f3f2ee; padding: 0 3px; border-radius: 3px; }
pre { background: #f7f6f2; border: 1px solid #e6e5e0; padding: 7pt 9pt; font-size: 8pt; line-height: 1.35; break-inside: avoid; }
pre code { background: none; padding: 0; }
figure { margin: 8pt 0 10pt; break-inside: avoid; }
figure img { width: 100%; }
figcaption { font-size: 8.4pt; font-style: italic; color: #55544f; margin-top: 3pt; }
p.note { font-size: 8pt; color: #55544f; margin-top: -2pt; }
p.tcap { font-size: 8.6pt; font-weight: 700; margin: 8pt 0 2pt; break-after: avoid; }
figure img { max-height: 4.3in; object-fit: contain; }
ul, ol { margin: 0 0 7pt; padding-left: 18pt; }
li { margin-bottom: 2pt; }
.appendix table { font-size: 7.6pt; }
.appendix td { padding: 2pt 4pt; }
.appendix td:nth-child(3), .appendix td:nth-child(4) { white-space: nowrap; }
"""


def pct(interval):
    low, high = interval
    return f"[{low:.0%}, {high:.0%}]"


def appendix_html(table):
    """One row per required result cell, with both decision rules and quality where measured."""
    rows = []
    for scheme in ORDER:
        for c in (c for c in table if c["scheme"] == scheme):
            if c["stage"] == "baseline":
                cell = f"F1 baseline, {c['kind']}"
            elif c["stage"] == "imprint":
                cell = f"F2 forgery, step {c['step']}"
            else:
                cell = f"F3 removal, {c['attack']}"
            n = c["observed_n"]
            native = f"{c['native_successes']}/{n} {pct(c['native_wilson95'])}"
            calibrated = f"{c['calibrated_successes']}/{n} {pct(c['calibrated_wilson95'])}"
            quality = ""
            if "psnr" in c:
                quality = "; ".join(
                    f"{label} {c[m]['mean']:.{digits}f} [{c[m]['bootstrap95'][0]:.{digits}f}, {c[m]['bootstrap95'][1]:.{digits}f}]"
                    for m, label, digits in [("psnr", "PSNR", 1), ("ssim", "SSIM", 3), ("lpips", "LPIPS", 3)]
                )
            rows.append(
                f"<tr><td>{NAMES[scheme]}</td><td>{cell}</td><td>{native}</td><td>{calibrated}</td><td>{quality}</td></tr>"
            )
    complete = sum(c["complete"] for c in table)
    return (
        '<section class="appendix"><h2>Appendix. Every result cell</h2>'
        f"<p>{complete} of {len(table)} required cells are complete. Counts are accepted / observed with 95% "
        "Wilson intervals. For F1 watermarked and every F2 and F3 cell, accepted means the watermark was detected; "
        "for F1 unwatermarked and real cells it is a false positive. The calibrated column for PRC is the separate "
        "score-only test. Quality is the mean over ten covers with a 10,000-resample bootstrap interval.</p>"
        "<table><thead><tr><th>Scheme</th><th>Cell</th><th>Native</th><th>Calibrated</th>"
        "<th>PSNR (dB) / SSIM / LPIPS</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></section>"
    )


def build_html(source, summary):
    body = markdown.markdown(
        Path(source).read_text(), extensions=["tables", "fenced_code", "md_in_html", "sane_lists"]
    )
    table = json.loads(Path(summary).read_text())
    base = Path(source).resolve().parent.as_uri() + "/"
    return (
        f'<!doctype html><html><head><meta charset="utf-8"><base href="{html.escape(base)}">'
        f"<title>Check-in 3</title><style>{CSS}</style></head><body>{body}{appendix_html(table)}</body></html>"
    )


def chrome():
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists() or shutil.which(candidate):
            return candidate
    raise RuntimeError("Google Chrome or Chromium is required to print the PDF")


def render(source, summary, out):
    out = Path(out).resolve()
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "checkin-3.html"
        page.write_text(build_html(source, summary))
        subprocess.run(
            [chrome(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             "--allow-file-access-from-files", f"--print-to-pdf={out}", page.as_uri()],
            check=True, capture_output=True,
        )
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default="docs/checkin-3.md")
    parser.add_argument("--summary", default="results/checkin3/full/summary-v2.json")
    parser.add_argument("--out", default="docs/Group6_CMPE261_CheckIn_3.pdf")
    args = parser.parse_args(argv)
    print("wrote", render(args.source, args.summary, args.out))


if __name__ == "__main__":
    main()
