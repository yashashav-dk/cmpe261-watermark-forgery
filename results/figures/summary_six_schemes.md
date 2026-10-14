Clean baseline, real-photo baseline and imprint forgery with a same-model attacker (C1). Brackets are 95 percent Wilson intervals.

| Scheme | TPR, watermarked | FPR, unwatermarked | FPR, real photos | Forgery success (imprint, C1) | Median first-detection step | PSNR / SSIM / LPIPS at last step | Seconds per imprint step |
|---|---|---|---|---|---|---|---|
| GS | 50/50 = 100% [93%, 100%] | 0/50 = 0% [0%, 7%] | 0/50 = 0% [0%, 7%] | 5/5 = 100% [57%, 100%] | 10 | 27.5 dB / 0.737 / 0.079 | 4.9 |
| PRC | 50/50 = 100% [93%, 100%] | 0/50 = 0% [0%, 7%] | 0/50 = 0% [0%, 7%] | 5/5 = 100% [57%, 100%] | 20 | 26.2 dB / 0.687 / 0.114 | 8.4 |
| RI | 49/50 = 98% [90%, 100%] | 0/50 = 0% [0%, 7%] | 0/50 = 0% [0%, 7%] | 5/5 = 100% [57%, 100%] | 70 | 24.3 dB / 0.607 / 0.184 | 8.4 |
| SFW | 49/50 = 98% [90%, 100%] | 0/50 = 0% [0%, 7%] | 0/50 = 0% [0%, 7%] | 5/5 = 100% [57%, 100%] | 90 | 23.9 dB / 0.596 / 0.200 | 8.4 |
| TR | 50/50 = 100% [93%, 100%] | 2/50 = 4% [1%, 13%] | 0/50 = 0% [0%, 7%] | 4/5 = 80% [38%, 96%] | 60 | 24.2 dB / 0.595 / 0.198 | 4.9 |
| WIND | 50/50 = 100% [93%, 100%] | 0/50 = 0% [0%, 7%] | 0/50 = 0% [0%, 7%] | 5/5 = 100% [57%, 100%] | 30 | 25.5 dB / 0.657 / 0.140 | 8.4 |

Imprint forgery per cover photograph

| Scheme | Covers forged | Stop step, median (range) | PSNR at stop, median (range) |
|---|---|---|---|
| Gaussian Shading | 5/5 = 100% [57%, 100%] | 10 (10 to 10) | 28.6 dB (22.7 to 31.8) |
| PRC | 5/5 = 100% [57%, 100%] | 20 (20 to 30) | 27.7 dB (22.0 to 30.5) |
| Ring-ID | 5/5 = 100% [57%, 100%] | 70 (50 to 120) | 26.0 dB (20.1 to 27.9) |
| SFW | 5/5 = 100% [57%, 100%] | 90 (80 to 140) | 25.1 dB (20.0 to 27.3) |
| Tree-Ring | 4/5 = 80% [38%, 96%] | 70 (50 to 150) | 26.0 dB (19.6 to 28.4) |
| WIND | 5/5 = 100% [57%, 100%] | 30 (30 to 50) | 27.0 dB (21.2 to 29.4) |
