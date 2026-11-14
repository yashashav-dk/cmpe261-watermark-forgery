"""Build the Check-in 4 PDF: docs/checkin-4.md -> styled HTML -> headless Chrome PDF.

Usage:
    python scripts/checkin4_pdf.py
    python scripts/checkin4_pdf.py --source docs/checkin-4.md --out docs/Group6_CMPE261_CheckIn_4.pdf
"""

from __future__ import annotations

import argparse
import html
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
figure img { width: 100%; max-height: 4.3in; object-fit: contain; }
figcaption { font-size: 8.4pt; font-style: italic; color: #55544f; margin-top: 3pt; }
p.note { font-size: 8pt; color: #55544f; margin-top: -2pt; }
p.tcap { font-size: 8.6pt; font-weight: 700; margin: 8pt 0 2pt; break-after: avoid; }
ul, ol { margin: 0 0 7pt; padding-left: 18pt; }
li { margin-bottom: 2pt; }
"""


def chrome():
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists() or shutil.which(candidate):
            return candidate
    raise RuntimeError("Google Chrome or Chromium is required to print the PDF")


def build_html(source: Path) -> str:
    body = markdown.markdown(
        source.read_text(), extensions=["tables", "fenced_code", "md_in_html", "sane_lists"]
    )
    base = source.resolve().parent.as_uri() + "/"
    return (
        f'<!doctype html><html><head><meta charset="utf-8"><base href="{html.escape(base)}">'
        f"<title>Check-in 4</title><style>{CSS}</style></head><body>{body}</body></html>"
    )


def render(source: Path, out: Path) -> Path:
    out = out.resolve()
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "checkin-4.html"
        page.write_text(build_html(source))
        subprocess.run(
            [
                chrome(),
                "--headless=new",
                "--disable-gpu",
                "--no-pdf-header-footer",
                "--allow-file-access-from-files",
                f"--print-to-pdf={out}",
                page.as_uri(),
            ],
            check=True,
            capture_output=True,
        )
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="docs/checkin-4.md")
    parser.add_argument("--out", default="docs/Group6_CMPE261_CheckIn_4.pdf")
    args = parser.parse_args(argv)
    print("wrote", render(Path(args.source), Path(args.out)))


if __name__ == "__main__":
    main()
