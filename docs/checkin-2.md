# Check-in 2

Forging the Watermark: Benchmarking False Attribution in Semantic Watermarks for Diffusion Models

CMPE 261 Sec 01, Fall 2026. Group 6.

- Kanaka Sarat Siripurapu, 019132776, kanakasarat.siripurapu@sjsu.edu
- Latha Boralingaiah, 018301361, latha.boralingaiah@sjsu.edu
- Yashashav Devalapalli Kamalraj, 017856371, yashashav.devalapallikamalraj@sjsu.edu

Repository: https://github.com/yashashav-dk/cmpe261-watermark-forgery

Shared Drive folder: https://drive.google.com/drive/folders/1wkXOxPjfI648JPod1Fi2m9ItfrPvWVIT

The instructor and the TA were invited to the repository and the Drive folder before Check-in 1 and still have access.

## 1. Where each requirement is met

| Requirement | Status | Where |
|---|---|---|
| Tentative abstract (recommended) | Done, revised | Section 3.1 |
| Report outline (recommended) | Done | Section 3.2 |
| Literature survey (recommended) | Done, first draft | Section 3.3 |
| Approach (required) | Done: full pipeline built and run end to end; two protocol variants compared | Section 4 |
| Algorithms (recommended) | Done: forgery attack and two detectors implemented and described | Section 5 |
| Meaningful check-ins (required) | 21 commits by three members, 6 by Kanaka Sarat Siripurapu | Section 7 and the repository history |
| Repository link in the report (required) | Done | Top of this document |
| Initial report draft (recommended) | Sections 3 to 6 are the draft of report sections 1 to 6 | This document; docs/ in the repository |

## 2. Progress since Check-in 1

Check-in 1 delivered the finalized specification, the software pipeline, and a first false-attribution measurement on two schemes. Since then the team has done the following.

- **Extended the first experiment.** A 150-step rerun of the Tree-Ring forgery on the same five photographs, which raised the success count from 2 of 5 to 4 of 5 and showed how thin the margins are near the detector threshold (Section 6).
- **Literature survey.** A survey of 16 papers covering the nine candidate schemes, the attacks the benchmark uses, and existing benchmarks, written up in Section 3.3. It settles the open question left in the specification about forgery evaluations of schemes other than Tree-Ring and Gaussian Shading.
- **Approach and algorithm write-up.** Sections 4 and 5 describe the pipeline as built, the two protocol choices that were tried, and the forgery and detection algorithms as pseudo-code, so a reader can check the implementation against the papers.
- **Repository documentation.** The project README now carries the findings so far and a status line against each floor commitment, and links the shared Drive folder.
What has not moved: the clean baseline for the other four core schemes (F1) and the removal-resistance runs (F3) have not started. They are the next two items and are sized in Section 8.

## 3. Draft of the report

### 3.1 Abstract

A semantic watermark hides a signal in the starting noise of a diffusion model and checks for it by inverting a candidate image back to that noise. Published evaluations of these schemes test almost only whether the signal survives edits. We study the opposite failure, false attribution: an attacker takes a real photograph that the provider never generated and modifies it until the provider's detector says it is watermarked. Building on the MarkDiffusion toolkit and the black-box imprint attack of Mueller et al., we benchmark six core semantic schemes, and up to three more, on Stable Diffusion 2.1-base. The headline number per scheme is the share of real photographs the detector accepts after the attack, measured at the toolkit default threshold and at a threshold set to a 1 percent false-positive rate, with the attacker using either the provider's model or a different one. Resistance to removal is reported next to forgeability so the two can be compared on the same schemes. First measurements show Gaussian Shading forged on 5 of 5 photographs within 10 optimization steps and Tree-Ring on 4 of 5 within 150 steps. All experiments are inference only and every rate carries a confidence interval.

### 3.2 Report outline

1. Introduction. Removal versus forgery, why false attribution matters for provenance, contributions.
1. Background and related work. Semantic watermarking and inversion-based detection, the nine schemes, removal attacks, forgery attacks, existing benchmarks (Section 3.3 below).
1. Threat model. Attacker knowledge and compute, what counts as a successful forgery, the three attacker-model conditions.
1. Benchmark design. Attacks added to MarkDiffusion, scheme inclusion rule, metrics, detector operating points, step budgets (Section 4).
1. Experimental setup. Models, data, sample sizes, statistics, compute.
1. Results. Clean baseline; false attribution by scheme and threshold; transfer across attacker models; resistance to removal versus forgeability; perceptual cost.
1. Discussion. Design properties that track forgery resistance, implications for provenance systems, limitations.
1. Conclusion and future work. References. Appendix with per-scheme configurations and excluded schemes.

### 3.3 Literature survey

**Schemes.** Semantic watermarks sit in the latent noise rather than in the pixels. Tree-Ring [1] writes a ring pattern into the Fourier transform of the initial noise and detects it by DDIM inversion [12] of the image followed by an L1 distance to the pattern. RingID [2] shows that part of Tree-Ring's apparent resistance to attacks comes from the distribution shift the pattern introduces, and redesigns the key so that many keys can be told apart. Gaussian Shading [3] instead maps a secret bit string to the initial noise through the Gaussian quantiles, which keeps the noise distribution unchanged and lets the detector recover bits and score bit accuracy. PRC [4] replaces the bit string with a pseudorandom error-correcting code and proves that watermarked and unwatermarked outputs are computationally indistinguishable. WIND [5] combines a Fourier group index with a salted family of initial noises so that retrieval is fast and the noise itself carries no fixed pattern. ROBIN [6] implants the watermark at an intermediate diffusion state and optimizes a hiding prompt so the final image shows no artifact. SEAL [7] ties the watermark to a caption of the image, so the key must agree with what the image shows. GaussMarker [8] embeds in both the spatial and the frequency domain and adds a learned restorer for noise recovered from edited images. MarkDiffusion [9] packages these schemes behind one interface with shared detection code, which is what makes a cross-scheme benchmark feasible in one semester.

**Removal.** The removal literature is large. WAVES [10] is the reference benchmark; it ranks watermarks under distortions, diffusion-based regeneration, and adversarial attacks, and the four distortion and purification attacks used here are the ones MarkDiffusion ships. Zhao et al. [11] show that regeneration through a diffusion model removes any pixel-space watermark of bounded strength, and DiffPure [13] is the purification procedure most such attacks reuse. UnMarker [14] attacks the spectral content directly and reaches semantic watermarks too. Saberi et al. [15] give the first fundamental limits for watermark-based detectors and include a spoofing attack, which is the earliest forgery result we found.

**Forgery.** Mueller et al. [16] is the direct ancestor of this project. Their imprint attack optimizes a cover image so that the attacker's inversion of it lands on the inverted noise of one watermarked reference, with no knowledge of the scheme, and their reprompting attack regenerates from an inverted reference under a new prompt. They evaluate Tree-Ring and Gaussian Shading only. A follow-up by a different group [17] forges and removes latent-noise watermarks from a single image and covers additional schemes, which partly answers the specification's open item: forgery evaluations now exist beyond the two original schemes, but not on a common model, threshold policy, or step budget, and not next to removal numbers. That gap is the one this benchmark fills.

**What the survey shows.** None of the scheme papers reports a false-attribution rate on real photographs. Benchmarks report removal only. Forgery results exist for a few schemes under differing protocols. A benchmark that reports forgeability and resistance to removal on the same schemes, same model, and same thresholds is missing.

## 4. Approach

**Framing.** The problem is treated as a measurement task, not a new attack. The pipeline has three parts that communicate only through images, so a new scheme or a new attack can be added on one side without touching the other.

- **Harness (src/wmforge/harness.py)** wraps MarkDiffusion. For a scheme it generates a watermarked or an unwatermarked image from a prompt and a seed, and runs the scheme's detector on any image, returning the raw score and the verdict. One correction was necessary because MarkDiffusion samples a scheme's starting noise a single time at load; the harness therefore reseeds and redraws the initial latents per image.
- **Attack (src/wmforge/imprint.py)** takes a cover photograph, a watermarked reference image, and an attacker pipeline, and returns the forged image and a per-step record. It is adapted from the official code of [16] and rewritten against MarkDiffusion's dependency set so that one environment runs everything.
- **Metrics and provenance (metrics.py, records.py, report.py)** compute rates with Wilson intervals, continuous metrics with bootstrap intervals, PSNR, SSIM, and LPIPS, and write one CSV row per (scheme, attack, condition, image, step) with seed and model commit hashes, so an interrupted run resumes from the log.
**Approaches explored, 1.** Two approaches were tried for the attack code. Running the reference implementation as is failed because its pinned packages conflict with MarkDiffusion's. Re-implementing the attack against MarkDiffusion's environment worked and is what the repository contains; the GPL-3.0 license of the original is kept.

**Approaches explored, 2.** Two run protocols were tried. Stopping at the first positive detection, with a cap, gives a median first-detection step and is cheap, but it uses the detector's verdict, which a real attacker does not have, and verdicts near the threshold flip between repeated runs. Running to a fixed step budget and reporting success at several budgets is more expensive but matches the threat model. Check-in 1 used the first protocol to measure cost; the benchmark proper uses the second. The 150-step Tree-Ring rerun is what showed the flip: one cover scored 50.02 at step 50 in one run and 49.67 in the next, against a threshold of 50.

**Approaches explored, 3.** Two precision settings were tried. Half precision halves memory but Gaussian Shading builds float32 latents that the half-precision pipeline rejects, so the target pipeline and the attack run in full precision with gradient checkpointing.

## 5. Algorithms

**Imprint forgery, adapted from [16].** The attacker has the reference image, its own diffusion model, and nothing about the scheme. It moves the cover's latent until the attacker's own inversion of it matches the inversion of the reference. The provider's detector is called only to record the outcome.

```
Input: cover image c, watermarked reference r, attacker pipeline (VAE, UNet, DDIM inverse scheduler), step cap K
1. z_target = Invert(Encode(r))              # no gradient; 50 DDIM inversion steps, empty prompt, no guidance
2. z = Encode(c), made a trainable parameter; Adam with learning rate 1e-2
3. for step in 1..K:
     loss = MSE( Invert(z), z_target )       # differentiable inversion, UNet activations recomputed on backward
     backprop, Adam step
     every 10 steps and at K: image = Decode(z); run the provider's detector; record score and verdict
4. return Decode(z) and the per-step records
```

**DDIM inversion [12], used by every detector and by the attack.** Reverse the sampler: starting from the clean latent, apply the DDIM update in the increasing-noise direction for 50 steps using the model's noise prediction with an empty prompt. Because DDIM is deterministic, inversion followed by generation returns close to the same image, which is what makes the recovered noise usable as a watermark channel.

**Tree-Ring detector [1].** Generation: sample noise, replace the magnitude of a ring of Fourier coefficients with the key, run the sampler. Detection: invert the image, take the Fourier transform of the recovered noise, and compute the L1 distance to the key inside the ring mask. MarkDiffusion's default flags an image when the distance is below 50. On this model watermarked generations scored 23 to 46, unwatermarked generations 47 to 62, and real photographs 50 to 61, so a real photograph starts only a few units from being flagged.

**Gaussian Shading detector [3].** Generation: expand a secret message into a bit string, map each bit to a sample of the standard normal by inverse-CDF sampling within the bit's half, and use the result as the initial noise. Detection: invert the image, read each latent entry's sign back to a bit, and compare with the key; the score is bit accuracy and the default threshold is 0.7. Untouched photographs scored 0.43 to 0.58 and forged ones 0.89 to 0.98.

**Statistics.** Rates use 95 percent Wilson intervals, which stay informative when every trial succeeds or fails; continuous metrics use 10,000-resample percentile bootstraps. The calibrated operating point sets each scheme's threshold to a 1 percent false-positive rate on 200 unwatermarked generations.

## 6. Results so far

Target: Stable Diffusion 2.1-base, 512 by 512, 50 sampling steps, guidance 7.5, full precision. Attacker: the same model (condition C1). 50 prompts, 50 COCO val2017 photographs, and 5 cover photographs per scheme. One NVIDIA RTX PRO 6000 on Colab. Brackets are 95 percent Wilson intervals.

| Scheme | TPR watermarked | FPR unwatermarked | FPR real photos | Forged, 60-step cap | Forged, 150-step cap | PSNR of forgeries |
|---|---|---|---|---|---|---|
| Gaussian Shading | 50/50 | 0/50 | 0/50 | 5/5 [57%, 100%], all by step 10 | not needed | 27.5 dB |
| Tree-Ring | 50/50 | 2/50 | 0/50 | 2/5 [12%, 77%] | 4/5 [38%, 96%] | 24.2 dB |

Gaussian Shading was forged on every photograph at the first check, about 49 seconds per cover. Tree-Ring is harder but not safe: two of its four successes sit just under the threshold, and repeated optimizations differ by about 0.3, so those verdicts are coin flips. Photographs that took more than 100 steps to forge ended near 20 dB PSNR, which is visible texture damage. One imprint step costs 4.9 seconds on this GPU; the full F2 item (six schemes, 10 covers) is about 12 GPU-hours at a 150-step budget.

## 7. Check-ins

The repository has 21 commits on the main branch by all three members, merged through one reviewed pull request. Each commit adds one component, one fix, or one document. The list below is the git log.

| Date | Member | Commit |
|---|---|---|
| 2026-10-02 | Yashashav | docs: link the shared Drive folder in the README |
| 2026-10-02 | Latha | docs: report findings so far in the README; add 150-step follow-up to check-in 1 |
| 2026-10-02 | Yashashav | results: add Tree-Ring imprint run with a 150-step cap |
| 2026-10-01 | Kanaka Sarat | docs: address the team in the check-in 1 plan |
| 2026-10-01 | Latha | docs: reword plan instructions |
| 2026-10-01 | Yashashav | docs: simplify commit commands in the check-in 1 plan |
| 2026-10-01 | Kanaka Sarat | Merge check-in 1: specification, forgery harness, first results (#1) |
| 2026-10-01 | Latha | docs: add check-in 1 write-up and project README |
| 2026-10-01 | Yashashav | results: add check-in 1 run outputs |
| 2026-10-01 | Kanaka Sarat | fix: keep imprint resume consistent with the log; optional Drive output |
| 2026-10-01 | Latha | fix: run target pipeline in fp32; drop stale torchaudio on Colab |
| 2026-10-01 | Yashashav | feat: add Colab notebook for the check-in 1 run |
| 2026-10-01 | Kanaka Sarat | feat: add run report with summary table and figures |
| 2026-10-01 | Latha | feat: add check-in 1 experiment runner |
| 2026-10-01 | Yashashav | feat: add imprint forgery attack |
| 2026-10-01 | Kanaka Sarat | feat: add MarkDiffusion harness with per-image seeding |
| 2026-10-01 | Latha | feat: add resumable CSV run log |
| 2026-10-01 | Yashashav | feat: add seeded data selection and cover loading |
| 2026-10-01 | Kanaka Sarat | feat: add package scaffold and metrics |
| 2026-10-01 | Latha | docs: add project specification and check-in 1 plan |
| 2026-10-01 | Yashashav | Add README with project title and team |

Commits per member: Yashashav 8, Latha 7, Kanaka Sarat 6. Member responsibilities are unchanged from the specification: Kanaka Sarat Siripurapu owns metrics, statistics, and the provenance layer; Latha Boralingaiah owns the attack implementation and transferability; Yashashav Devalapalli Kamalraj owns the generation harness and environment.

## 8. Next steps and risks

1. F1: clean baseline and real-photo baseline for the remaining four core schemes (Ring-ID, SFW, WIND, PRC) at the specification's sample sizes. Each scheme is about 400 generations and detections, under one GPU-hour.
1. F2: imprint forgery under C1 for all six core schemes, 10 covers each, at fixed step budgets of 50, 100, and 150, about 12 GPU-hours total.
1. F3: resistance to removal under JPEG, blur, crop-and-scale, and diffusion purification, 100 watermarked images per scheme and attack.
1. Then T1: the same forgery with Stable Diffusion 1.5 as the attacker.
**Risks.** The main risk is Colab quota on a single Pro account; runs resume from the CSV log, and the step cap is lowered before the cover count. A scheme that fails the inclusion rule on the clean baseline is reported as excluded. CoE HPC access is still unconfirmed and no floor item depends on it.

## References

[1] Y. Wen, J. Kirchenbauer, J. Geiping, T. Goldstein. Tree-Ring Watermarks: Fingerprints for Diffusion Images that are Invisible and Robust. NeurIPS 2023. arXiv:2305.20030.
[2] H. Ci, P. Yang, Y. Song, M. Z. Shou. RingID: Rethinking Tree-Ring Watermarking for Enhanced Multi-Key Identification. ECCV 2024. arXiv:2404.14055.
[3] Z. Yang et al. Gaussian Shading: Provable Performance-Lossless Image Watermarking for Diffusion Models. CVPR 2024. arXiv:2404.04956.
[4] S. Gunn, X. Zhao, D. Song. An Undetectable Watermark for Generative Image Models. 2024. arXiv:2410.07369.
[5] K. Arabi, B. Feuer, R. T. Witter, C. Hegde, N. Cohen. Hidden in the Noise: Two-Stage Robust Watermarking for Images. 2024. arXiv:2412.04653.
[6] H. Huang, Y. Wu, Q. Wang. ROBIN: Robust and Invisible Watermarks for Diffusion Models with Adversarial Optimization. NeurIPS 2024. arXiv:2411.03862.
[7] K. Arabi, R. T. Witter, C. Hegde, N. Cohen. SEAL: Semantic Aware Image Watermarking. 2025. arXiv:2503.12172.
[8] K. Li et al. GaussMarker: Robust Dual-Domain Watermark for Diffusion Models. ICML 2025. arXiv:2506.11444.
[9] L. Pan et al. MarkDiffusion: An Open-Source Toolkit for Generative Watermarking of Latent Diffusion Models. 2025. arXiv:2509.10569.
[10] B. An et al. WAVES: Benchmarking the Robustness of Image Watermarks. ICML 2024.
[11] X. Zhao et al. Invisible Image Watermarks Are Provably Removable Using Generative AI. NeurIPS 2024. arXiv:2306.01953.
[12] J. Song, C. Meng, S. Ermon. Denoising Diffusion Implicit Models. ICLR 2021. arXiv:2010.02502.
[13] W. Nie et al. Diffusion Models for Adversarial Purification. ICML 2022. arXiv:2205.07460.
[14] A. Kassis, U. Hengartner. UnMarker: A Universal Attack on Defensive Image Watermarking. IEEE S&P 2025. arXiv:2405.08363.
[15] M. Saberi et al. Robustness of AI-Image Detectors: Fundamental Limits and Practical Attacks. ICLR 2024. arXiv:2310.00076.
[16] A. Mueller, D. Lukovnikov, J. Thietke, A. Fischer, E. Quiring. Black-Box Forgery Attacks on Semantic Watermarks for Diffusion Models. CVPR 2025. arXiv:2412.03283.
[17] Forging and Removing Latent-Noise Diffusion Watermarks Using a Single Image. 2025. arXiv:2504.20111.