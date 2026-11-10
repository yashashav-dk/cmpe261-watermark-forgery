# Check-in 4 offline analysis of the Check-in 3 floor

Recomputed from `results/checkin3/full/measurements-v2.json`. No new GPU work.

## Forgeability order (native first acceptance)

| Scheme | Accepted by step 150 | Median first step | Range | Calibrated at step 150 |
|---|---|---|---|---|
| Gaussian Shading | 10/10 | 10.0 | 10 to 10 | 10/10 |
| PRC | 10/10 | 30.0 | 20 to 40 | 10/10 |
| WIND | 10/10 | 40.0 | 30 to 70 | 10/10 |
| Tree-Ring | 6/10 | 65.0 | 50 to 120 | 6/10 |
| SFW | 7/10 | 90 | 80 to 150 | 10/10 |
| Ring-ID | 6/10 | 90.0 | 60 to 140 | 10/10 |

## Native versus calibrated disagreement

| Scheme | Stage | N | Native only | Calibrated only | Disagree |
|---|---|---|---|---|---|
| Tree-Ring | baseline | 400 | 8 | 0 | 8 |
| Tree-Ring | imprint | 30 | 1 | 0 | 1 |
| Tree-Ring | removal | 400 | 33 | 0 | 33 |
| Ring-ID | baseline | 400 | 0 | 7 | 7 |
| Ring-ID | imprint | 30 | 0 | 18 | 18 |
| Ring-ID | removal | 400 | 0 | 181 | 181 |
| SFW | baseline | 400 | 0 | 5 | 5 |
| SFW | imprint | 30 | 0 | 19 | 19 |
| SFW | removal | 400 | 0 | 192 | 192 |
| Gaussian Shading | baseline | 400 | 0 | 4 | 4 |
| Gaussian Shading | imprint | 30 | 0 | 0 | 0 |
| Gaussian Shading | removal | 400 | 0 | 0 | 0 |
| WIND | baseline | 400 | 0 | 7 | 7 |
| WIND | imprint | 30 | 0 | 3 | 3 |
| WIND | removal | 400 | 0 | 125 | 125 |
| PRC | baseline | 400 | 0 | 2 | 2 |
| PRC | imprint | 30 | 0 | 0 | 0 |
| PRC | removal | 400 | 0 | 37 | 37 |

## Removal survival gap (calibrated minus native)

| Scheme | Attack | Native | Calibrated | Gap |
|---|---|---|---|---|
| Tree-Ring | jpeg | 99/100 | 99/100 | +0 |
| Tree-Ring | blur | 41/100 | 30/100 | -11 |
| Tree-Ring | crop | 83/100 | 77/100 | -6 |
| Tree-Ring | purification | 45/100 | 29/100 | -16 |
| Ring-ID | jpeg | 87/100 | 100/100 | +13 |
| Ring-ID | blur | 36/100 | 100/100 | +64 |
| Ring-ID | crop | 0/100 | 9/100 | +9 |
| Ring-ID | purification | 0/100 | 95/100 | +95 |
| SFW | jpeg | 90/100 | 100/100 | +10 |
| SFW | blur | 20/100 | 100/100 | +80 |
| SFW | crop | 0/100 | 2/100 | +2 |
| SFW | purification | 0/100 | 100/100 | +100 |
| Gaussian Shading | jpeg | 100/100 | 100/100 | +0 |
| Gaussian Shading | blur | 100/100 | 100/100 | +0 |
| Gaussian Shading | crop | 0/100 | 0/100 | +0 |
| Gaussian Shading | purification | 100/100 | 100/100 | +0 |
| WIND | jpeg | 98/100 | 100/100 | +2 |
| WIND | blur | 79/100 | 100/100 | +21 |
| WIND | crop | 0/100 | 2/100 | +2 |
| WIND | purification | 0/100 | 100/100 | +100 |
| PRC | jpeg | 99/100 | 99/100 | +0 |
| PRC | blur | 96/100 | 98/100 | +2 |
| PRC | crop | 0/100 | 2/100 | +2 |
| PRC | purification | 6/100 | 39/100 | +33 |

## Image quality pooled across schemes

| Budget | N | Mean PSNR (dB) | Mean SSIM | Mean LPIPS |
|---|---|---|---|---|
| step 50 | 60 | 22.18 | 0.567 | 0.170 |
| step 100 | 60 | 21.10 | 0.513 | 0.222 |
| step 150 | 60 | 20.45 | 0.482 | 0.262 |
