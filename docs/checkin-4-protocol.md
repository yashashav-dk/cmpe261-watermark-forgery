# Check-in 4 protocol

Pinned choices for the target items started after Check-in 3. The floor (F1 to F3) is frozen; this document only covers C2 imprint and the strength sweeps.

## Shared with Check-in 3

- Provider model: `Manojb/stable-diffusion-2-1-base` @ `0094d483a120f3f33dafbd187ea4aa60d10de75c`
- MarkDiffusion commit: the pin in `wmforge.data.MARKDIFFUSION_SHA`
- Covers: first 10 ids in `data/coco_val2017_checkin3.txt`
- Keys: `results/checkin3/full/keys/{scheme}.pkl`
- Calibrations: `results/checkin3/full/{scheme}-calibration.json`
- Budgets: score at steps 50, 100 and 150; never stop early
- Seed: 261 for selection; imprint cover i uses seed `10000 + i`

## Condition C2

- Attacker: `stable-diffusion-v1-5/stable-diffusion-v1-5` @ `451f4fe16113bdc1c2ae000260dc525a8138637d`
- Command: `python -m wmforge.checkin4 c2-imprint --checkin3 results/checkin3/full --out results/checkin4/c2`
- Detection still uses the provider pipeline and the Check-in 3 keys
- Output identity is bound in `results/checkin4/c2/manifest.json`

## Strength sweeps

- Crop ratios: 0.95, 0.90, 0.85, 0.80, 0.70, 0.60
- Purification strengths: 0.10, 0.20, 0.30, 0.40, 0.50
- Command: `python -m wmforge.checkin4 sweep --checkin3 results/checkin3/full --out results/checkin4/sweeps`
- Sources are the Check-in 3 watermarked baselines; artifacts are re-saved under the sweep tree

## Offline draft analysis

No GPU. Recomputes tables and figures for the report draft:

```
PYTHONPATH=src python scripts/checkin4_analysis.py
```

Writes `results/checkin4/analysis/` and `results/checkin4/figures/`.
