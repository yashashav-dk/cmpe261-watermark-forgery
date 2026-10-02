"""Draw imprint trajectories from several runs in one figure, one panel per scheme."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from wmforge import report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", help="SCHEME=results/dir pairs; each run contributes one scheme")
    parser.add_argument("--out", default="results/figures/trajectories.png")
    args = parser.parse_args()

    frames = []
    for item in args.runs:
        scheme, run_dir = item.split("=", 1)
        df = report.load(Path(run_dir) / "runs.csv")
        frames.append(df[df.scheme == scheme])
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    report.plot_trajectories(pd.concat(frames, ignore_index=True), out)
    print(out)


if __name__ == "__main__":
    main()
