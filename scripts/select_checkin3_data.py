"""Extend historical inputs deterministically without modifying their prefixes."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import pandas as pd

from wmforge import data
from wmforge.benchmark import extend_selection, bind_manifest, digest
from select_data import download


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path("data/.cache"))
    args = parser.parse_args()
    prompt_pool = args.cache / "sd_prompts_eval.parquet"
    captions = args.cache / "annotations_trainval2017.zip"
    download(data.PROMPTS_URL, prompt_pool)
    coco_source = "https://s3.amazonaws.com/images.cocodataset.org/annotations/annotations_trainval2017.zip"
    download(coco_source, captions)
    prompts = pd.read_parquet(prompt_pool)["Prompt"].tolist()
    prompts = sorted(
        {" ".join(p.split()) for p in prompts if isinstance(p, str) and p.strip()}
    )
    with zipfile.ZipFile(captions) as archive:
        ids = [
            r["id"]
            for r in json.loads(archive.read(data.COCO_CAPTIONS_MEMBER))["images"]
        ]
    selections = {
        Path("data/prompts_checkin3.txt"): extend_selection(
            data.read_lines("data/prompts_checkin1.txt"), prompts, 200
        ),
        Path("data/coco_val2017_checkin3.txt"): extend_selection(
            data.read_image_ids("data/coco_val2017_checkin1.txt"), ids, 100
        ),
    }
    for path, values in selections.items():
        expected = "".join(f"{v}\n" for v in values)
        if path.exists() and path.read_text() != expected:
            raise ValueError(f"{path}: existing selection differs; refusing overwrite")
        data.write_lines(path, values)
        print(f"{path}: {len(values)} inputs, seed 261; historical 50 preserved")
    bind_manifest(
        "data/checkin3-selection.json",
        dict(
            seed=261,
            historical_prefix_count=50,
            prompts_count=200,
            photographs_count=100,
            prompt_pool=dict(
                url=data.PROMPTS_URL,
                sha256=digest(prompt_pool),
                unique_count=len(prompts),
            ),
            photograph_pool=dict(
                url=coco_source,
                member=data.COCO_CAPTIONS_MEMBER,
                sha256=digest(captions),
                unique_count=len(set(ids)),
            ),
            selections={str(path): digest(path) for path in selections},
            prefixes={
                name: digest(name)
                for name in [
                    "data/prompts_checkin1.txt",
                    "data/coco_val2017_checkin1.txt",
                ]
            },
        ),
    )


if __name__ == "__main__":
    main()
