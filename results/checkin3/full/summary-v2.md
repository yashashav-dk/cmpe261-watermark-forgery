# Check-in 3 progress and measurements

Only exact step-50, step-100, and step-150 images enter forgery results. Rates below use observed items; incomplete cells are provisional and never substitute for the required denominator.

Calibration is an empirical operating point on 200 generated negatives (0.5-percentage-point resolution). It is not independent evidence of population FPR. PRC score-only decisions are separate from native decoder verdicts.

| Scheme | Stage | Kind / attack / step | Observed / required | Native rate [Wilson 95%] | Calibrated rate [Wilson 95%] |
|---|---|---|---|---|---|
| TR | baseline | watermarked | 100/100 | 99.0% [94.6%, 99.8%] | 99.0% [94.6%, 99.8%] |
| TR | baseline | unwatermarked | 200/200 | 4.0% [2.0%, 7.7%] | 1.0% [0.3%, 3.6%] |
| TR | baseline | real | 100/100 | 2.0% [0.6%, 7.0%] | 0.0% [0.0%, 3.7%] |
| TR | imprint | imprint / 50 | 10/10 | 20.0% [5.7%, 51.0%] | 10.0% [1.8%, 40.4%] |
| TR | imprint | imprint / 100 | 10/10 | 50.0% [23.7%, 76.3%] | 50.0% [23.7%, 76.3%] |
| TR | imprint | imprint / 150 | 10/10 | 60.0% [31.3%, 83.2%] | 60.0% [31.3%, 83.2%] |
| TR | removal | jpeg | 100/100 | 99.0% [94.6%, 99.8%] | 99.0% [94.6%, 99.8%] |
| TR | removal | blur | 100/100 | 41.0% [31.9%, 50.8%] | 30.0% [21.9%, 39.6%] |
| TR | removal | crop | 100/100 | 83.0% [74.5%, 89.1%] | 77.0% [67.8%, 84.2%] |
| TR | removal | purification | 100/100 | 45.0% [35.6%, 54.8%] | 29.0% [21.0%, 38.5%] |
| RI | baseline | watermarked | 100/100 | 95.0% [88.8%, 97.8%] | 100.0% [96.3%, 100.0%] |
| RI | baseline | unwatermarked | 200/200 | 0.0% [0.0%, 1.9%] | 1.0% [0.3%, 3.6%] |
| RI | baseline | real | 100/100 | 0.0% [0.0%, 3.7%] | 0.0% [0.0%, 3.7%] |
| RI | imprint | imprint / 50 | 10/10 | 0.0% [0.0%, 27.8%] | 90.0% [59.6%, 98.2%] |
| RI | imprint | imprint / 100 | 10/10 | 50.0% [23.7%, 76.3%] | 100.0% [72.2%, 100.0%] |
| RI | imprint | imprint / 150 | 10/10 | 60.0% [31.3%, 83.2%] | 100.0% [72.2%, 100.0%] |
| RI | removal | jpeg | 100/100 | 87.0% [79.0%, 92.2%] | 100.0% [96.3%, 100.0%] |
| RI | removal | blur | 100/100 | 36.0% [27.3%, 45.8%] | 100.0% [96.3%, 100.0%] |
| RI | removal | crop | 100/100 | 0.0% [0.0%, 3.7%] | 9.0% [4.8%, 16.2%] |
| RI | removal | purification | 100/100 | 0.0% [0.0%, 3.7%] | 95.0% [88.8%, 97.8%] |
| SFW | baseline | watermarked | 100/100 | 97.0% [91.5%, 99.0%] | 100.0% [96.3%, 100.0%] |
| SFW | baseline | unwatermarked | 200/200 | 0.0% [0.0%, 1.9%] | 1.0% [0.3%, 3.6%] |
| SFW | baseline | real | 100/100 | 0.0% [0.0%, 3.7%] | 0.0% [0.0%, 3.7%] |
| SFW | imprint | imprint / 50 | 10/10 | 0.0% [0.0%, 27.8%] | 100.0% [72.2%, 100.0%] |
| SFW | imprint | imprint / 100 | 10/10 | 40.0% [16.8%, 68.7%] | 100.0% [72.2%, 100.0%] |
| SFW | imprint | imprint / 150 | 10/10 | 70.0% [39.7%, 89.2%] | 100.0% [72.2%, 100.0%] |
| SFW | removal | jpeg | 100/100 | 90.0% [82.6%, 94.5%] | 100.0% [96.3%, 100.0%] |
| SFW | removal | blur | 100/100 | 20.0% [13.3%, 28.9%] | 100.0% [96.3%, 100.0%] |
| SFW | removal | crop | 100/100 | 0.0% [0.0%, 3.7%] | 2.0% [0.6%, 7.0%] |
| SFW | removal | purification | 100/100 | 0.0% [0.0%, 3.7%] | 100.0% [96.3%, 100.0%] |
| GS | baseline | watermarked | 100/100 | 100.0% [96.3%, 100.0%] | 100.0% [96.3%, 100.0%] |
| GS | baseline | unwatermarked | 200/200 | 0.0% [0.0%, 1.9%] | 1.0% [0.3%, 3.6%] |
| GS | baseline | real | 100/100 | 0.0% [0.0%, 3.7%] | 2.0% [0.6%, 7.0%] |
| GS | imprint | imprint / 50 | 10/10 | 100.0% [72.2%, 100.0%] | 100.0% [72.2%, 100.0%] |
| GS | imprint | imprint / 100 | 10/10 | 100.0% [72.2%, 100.0%] | 100.0% [72.2%, 100.0%] |
| GS | imprint | imprint / 150 | 10/10 | 100.0% [72.2%, 100.0%] | 100.0% [72.2%, 100.0%] |
| GS | removal | jpeg | 100/100 | 100.0% [96.3%, 100.0%] | 100.0% [96.3%, 100.0%] |
| GS | removal | blur | 100/100 | 100.0% [96.3%, 100.0%] | 100.0% [96.3%, 100.0%] |
| GS | removal | crop | 100/100 | 0.0% [0.0%, 3.7%] | 0.0% [0.0%, 3.7%] |
| GS | removal | purification | 100/100 | 100.0% [96.3%, 100.0%] | 100.0% [96.3%, 100.0%] |
| WIND | baseline | watermarked | 100/100 | 99.0% [94.6%, 99.8%] | 100.0% [96.3%, 100.0%] |
| WIND | baseline | unwatermarked | 200/200 | 0.0% [0.0%, 1.9%] | 1.0% [0.3%, 3.6%] |
| WIND | baseline | real | 100/100 | 0.0% [0.0%, 3.7%] | 4.0% [1.6%, 9.8%] |
| WIND | imprint | imprint / 50 | 10/10 | 70.0% [39.7%, 89.2%] | 100.0% [72.2%, 100.0%] |
| WIND | imprint | imprint / 100 | 10/10 | 100.0% [72.2%, 100.0%] | 100.0% [72.2%, 100.0%] |
| WIND | imprint | imprint / 150 | 10/10 | 100.0% [72.2%, 100.0%] | 100.0% [72.2%, 100.0%] |
| WIND | removal | jpeg | 100/100 | 98.0% [93.0%, 99.4%] | 100.0% [96.3%, 100.0%] |
| WIND | removal | blur | 100/100 | 79.0% [70.0%, 85.8%] | 100.0% [96.3%, 100.0%] |
| WIND | removal | crop | 100/100 | 0.0% [0.0%, 3.7%] | 2.0% [0.6%, 7.0%] |
| WIND | removal | purification | 100/100 | 0.0% [0.0%, 3.7%] | 100.0% [96.3%, 100.0%] |
| PRC | baseline | watermarked | 100/100 | 100.0% [96.3%, 100.0%] | 100.0% [96.3%, 100.0%] |
| PRC | baseline | unwatermarked | 200/200 | 0.0% [0.0%, 1.9%] | 1.0% [0.3%, 3.6%] |
| PRC | baseline | real | 100/100 | 0.0% [0.0%, 3.7%] | 0.0% [0.0%, 3.7%] |
| PRC | imprint | imprint / 50 | 10/10 | 100.0% [72.2%, 100.0%] | 100.0% [72.2%, 100.0%] |
| PRC | imprint | imprint / 100 | 10/10 | 100.0% [72.2%, 100.0%] | 100.0% [72.2%, 100.0%] |
| PRC | imprint | imprint / 150 | 10/10 | 100.0% [72.2%, 100.0%] | 100.0% [72.2%, 100.0%] |
| PRC | removal | jpeg | 100/100 | 99.0% [94.6%, 99.8%] | 99.0% [94.6%, 99.8%] |
| PRC | removal | blur | 100/100 | 96.0% [90.2%, 98.4%] | 98.0% [93.0%, 99.4%] |
| PRC | removal | crop | 100/100 | 0.0% [0.0%, 3.7%] | 2.0% [0.6%, 7.0%] |
| PRC | removal | purification | 100/100 | 6.0% [2.8%, 12.5%] | 39.0% [30.0%, 48.8%] |

Continuous metrics and their 10,000-resample bootstrap intervals are in `summary-v2.json`. Missing or infinite metric values are excluded explicitly through each metric’s `n_finite` count.