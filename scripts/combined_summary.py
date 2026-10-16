"""Summary tables across several run logs, one scheme per run, with Wilson intervals."""
from __future__ import annotations

import argparse
from pathlib import Path

from wmforge import report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "runs",
        nargs="+",
        help="SCHEME=results/dir or SCHEME:stage,stage=results/dir; each entry contributes one scheme, optionally one or more stages",
    )
    parser.add_argument("--out", default="results/figures/summary.md")
    args = parser.parse_args()

    sources = []
    for item in args.runs:
        selector, run_dir = item.split("=", 1)
        scheme, _, stages = selector.partition(":")
        frame = report.load(Path(run_dir) / "runs.csv")
        sources.append((scheme, frame, stages.split(",") if stages else None))
    df = report.combine_runs(sources)
    text = (
        "Clean baseline, real-photo baseline and imprint forgery with a same-model attacker (C1). "
        "Brackets are 95 percent Wilson intervals.\n\n"
        + report.summary_markdown(df)
        + "\nImprint forgery per cover photograph\n\n"
        + report.per_cover_markdown(df)
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
