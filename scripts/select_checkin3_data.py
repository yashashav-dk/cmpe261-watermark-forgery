"""Extend historical inputs deterministically without modifying their prefixes."""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import pandas as pd

from wmforge import data
from wmforge.benchmark import extend_selection
from select_data import download


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=Path('data/.cache'))
    args=parser.parse_args()
    prompt_pool=args.cache/'sd_prompts_eval.parquet'
    captions=args.cache/'annotations_trainval2017.zip'
    download(data.PROMPTS_URL,prompt_pool)
    download(data.COCO_ANNOTATIONS_URL,captions)
    prompts=pd.read_parquet(prompt_pool)['Prompt'].tolist()
    prompts=sorted({' '.join(p.split()) for p in prompts if isinstance(p,str) and p.strip()})
    with zipfile.ZipFile(captions) as archive:
        ids=[r['id'] for r in json.loads(archive.read(data.COCO_CAPTIONS_MEMBER))['images']]
    selections={
        Path('data/prompts_checkin3.txt'):extend_selection(data.read_lines('data/prompts_checkin1.txt'),prompts,200),
        Path('data/coco_val2017_checkin3.txt'):extend_selection(data.read_image_ids('data/coco_val2017_checkin1.txt'),ids,100),
    }
    for path,values in selections.items():
        expected=''.join(f'{v}\n' for v in values)
        if path.exists() and path.read_text()!=expected:
            raise ValueError(f'{path}: existing selection differs; refusing overwrite')
        data.write_lines(path,values)
        print(f'{path}: {len(values)} inputs, seed 261; historical 50 preserved')


if __name__=='__main__':
    main()
