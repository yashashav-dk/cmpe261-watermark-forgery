"""Select the check-in 1 prompt and cover-image subsets and write them to data/."""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import pandas as pd
import requests

from wmforge import data


def download(url: str, path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".part")
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with partial.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                handle.write(chunk)
    partial.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--seed", type=int, default=261)
    parser.add_argument("--cache", type=Path, default=Path("data/.cache"))
    parser.add_argument("--out", type=Path, default=Path("data"))
    args = parser.parse_args()

    prompts_path = args.cache / "sd_prompts_eval.parquet"
    download(data.PROMPTS_URL, prompts_path)
    prompts = pd.read_parquet(prompts_path)["Prompt"].tolist()

    annotations_path = args.cache / "annotations_trainval2017.zip"
    download(data.COCO_ANNOTATIONS_URL, annotations_path)
    with zipfile.ZipFile(annotations_path) as archive:
        captions = json.loads(archive.read(data.COCO_CAPTIONS_MEMBER))
    image_ids = [image["id"] for image in captions["images"]]

    chosen_prompts = data.select_prompts(prompts, args.n, args.seed)
    chosen_ids = data.select_image_ids(image_ids, args.n, args.seed)
    data.write_lines(args.out / "prompts_checkin1.txt", chosen_prompts)
    data.write_lines(args.out / "coco_val2017_checkin1.txt", chosen_ids)
    print(
        f"wrote {len(chosen_prompts)} prompts (from {len(prompts)} rows) and "
        f"{len(chosen_ids)} image ids (from {len(set(image_ids))} val2017 images)"
    )


if __name__ == "__main__":
    main()
