# Data

No dataset files or model weights are stored in this repository. Everything is fetched at run time and cached under `data/.cache/`, which git ignores.

| Source | Use | Where it comes from |
|---|---|---|
| Stable-Diffusion-Prompts, eval split | Prompts for generated images | `dataset/stable_diffusion_prompts/data/eval.parquet` in MarkDiffusion at commit `9d81656d` |
| MS-COCO val2017 | Real photographs: forgery covers and real-photo negatives | `http://images.cocodataset.org/val2017/<12-digit id>.jpg` |
| Stable Diffusion 2.1-base | Target model and same-model attacker | `Manojb/stable-diffusion-2-1-base` on Hugging Face, revision `0094d483` |

## Committed selections

| File | Contents |
|---|---|
| `prompts_checkin1.txt` | 50 prompts, one per line, whitespace collapsed |
| `coco_val2017_checkin1.txt` | 50 COCO val2017 image identifiers, one per line |

Both were drawn with seed 261 by `scripts/select_data.py`. Line order is the sample order: the clean baseline uses all 50 prompts, the real-photo baseline uses all 50 photographs, and imprint forgery uses the first 5 photographs as covers with the first 5 prompts for the watermarked references.

To regenerate: `python scripts/select_data.py`. The script downloads the prompt file (1 MB) and the COCO annotation archive (253 MB) on first use.

Cover photographs are centre-cropped to a square and resized to 512×512 RGB before use.
