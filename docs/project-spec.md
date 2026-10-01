# Project Specification

**Forging the Watermark: Benchmarking False Attribution in Semantic Watermarks for Diffusion Models**

CMPE 261 Sec 01 (Generative AI), SJSU, Fall 2026. Finalized after proposal feedback; last updated 2026-10-01.

Team: Kanaka Sarat Siripurapu, Latha Boralingaiah, Yashashav Devalapalli Kamalraj.

## 1. Changes since the proposal

The instructor's feedback (2026-09-29) requested no changes and asked to see results soon. The changes below come from inspecting the two codebases the project builds on. Each one narrows or sharpens a proposal commitment; none adds scope.

| # | Proposal said | Specification says | Reason |
|---|---|---|---|
| 1 | Eleven semantic schemes on SD 2.1-base | Nine image schemes exist; six are committed, three are added if they run without training | Two of MarkDiffusion's eleven algorithms target video models. Three image schemes depend on extra pretrained assets (section 3.1) |
| 2 | Add forgery, UnMarker, and surrogate-adversarial attacks | Forgery is committed. UnMarker and surrogate-adversarial are stretch goals | Forgery is the research question. No official UnMarker implementation was located, and the proposal did not define the surrogate-adversarial attack |
| 3 | Removal robustness reported alongside | Committed, using four attacks MarkDiffusion already implements | Keeps the robustness-versus-forgeability comparison without new attack code |
| 4 | Three source-model conditions including cross-architecture | Same-model is committed, a second Stable Diffusion model is the target, cross-architecture is a stretch goal | The reference attack code supports only Stable Diffusion attackers; a different architecture needs a new differentiable pipeline |
| 5 | 200 to 500 images per cell for every measurement | 100 to 200 for cheap measurements; 10 to 25 for imprint forgery | Imprint forgery is a per-image optimization; the reference implementation reports up to 40 minutes per image on an A40 |
| 6 | Bootstrap confidence intervals throughout | Wilson intervals for rates, bootstrap for continuous metrics | A bootstrap interval collapses to a single point when every trial succeeds or every trial fails, which is likely at small n |
| 7 | Real photographs, source unnamed | MS-COCO val2017 | Same cover-image source as the reference forgery implementation |
| 8 | Stable Diffusion 2.1-base | A pinned community mirror of the same weights | Stability AI removed the original repository from Hugging Face |
| 9 | CoE HPC only | Colab Pro for development and small runs, CoE HPC for larger runs if access is granted | Colab is available now; no committed result depends on HPC access |

Results-first ordering is the response to the feedback: check-in 1 carries a first false-attribution measurement (section 8).

## 2. Research question

Semantic watermarks are evaluated almost entirely against removal. This project measures the opposite failure: how often can an attacker make an innocent real photograph verify as watermarked, and does that rate depend on the watermarking scheme, the detector threshold, and the model the attacker uses?

A scheme that resists forgery is as reportable as one that does not.

## 3. Scope

### 3.1 Target model and schemes

The watermarking provider runs Stable Diffusion 2.1-base (512×512, 50 steps, guidance scale 7.5, DDIM inversion at detection) through MarkDiffusion 1.0.2 with each scheme's bundled default configuration.

| Group | Schemes | Extra requirements |
|---|---|---|
| Core (six) | Tree-Ring, Ring-ID, SFW, WIND (pattern-based); Gaussian Shading, PRC (key-based) | None; configuration only |
| Extended (three) | GaussMarker | Two pretrained checkpoints downloaded from Hugging Face |
| | ROBIN | A pretrained watermark, or a 2,000-step optimization if it is unavailable |
| | SEAL | A BLIP-2 captioning model and a sentence-embedding model loaded next to the diffusion model |

Tree-Ring and Gaussian Shading are the two schemes evaluated in [1]. The other four core schemes were not part of that evaluation.

**Inclusion rule.** A scheme enters the benchmark only if it runs under MarkDiffusion without any training and reaches a true-positive rate of at least 90% and a false-positive rate of at most 5% on the clean baseline at its default threshold. A scheme that fails is reported as excluded, with the reason. Forgery numbers for a detector that does not work on clean images would be meaningless.

VideoShield and VideoMark are out of scope.

### 3.2 Attacks

| Attack | Type | Source | Cost per image |
|---|---|---|---|
| JPEG compression, Gaussian blur, crop-and-scale | Removal (distortion) | Already in MarkDiffusion | One detection |
| Diffusion purification | Removal (regeneration) | Already in MarkDiffusion | One regeneration and one detection |
| Imprint forgery | Forgery | Adapted from the official implementation of [1] | Minutes (optimization) |
| Reprompting | Forgery | Adapted from the official implementation of [1] | About 30 seconds |
| UnMarker | Removal | Re-implemented from [3] | Unknown |
| Surrogate-adversarial | Removal | Not yet defined | Unknown |

The imprint loss is the distance between two latents inverted by the attacker's model (cover image and watermarked reference). It does not reference the watermarking scheme, so one implementation covers every scheme. MarkDiffusion supplies the watermarked reference and the detection verdict.

### 3.3 Attacker-model conditions

| Condition | Attacker model | Relation to target |
|---|---|---|
| C1 | SD 2.1-base | Same model; upper bound on attack strength |
| C2 | SD 1.5 | Same architecture family, different weights |
| C3 | PixArt-Σ | Different architecture (DiT) |

Reprompting uses only standard generation and inversion, so it can run under C3 with stock pipelines. Imprint forgery under C3 needs a new differentiable inversion pipeline.

### 3.4 Commitments

Work is ordered so that stopping after any item leaves a complete, reportable result.

**Floor.** The final report contains these regardless of what else is finished.

| # | Work | Size |
|---|---|---|
| F1 | Clean baseline and real-photo baseline, six core schemes | 100 watermarked generations, 200 unwatermarked generations, 100 real photographs per scheme |
| F2 | Imprint forgery under C1, six core schemes | 10 cover images per scheme |
| F3 | Removal robustness under the four existing attacks, six core schemes | 100 watermarked images per scheme and attack |

**Target.** Done in this order once the floor is complete.

| # | Work |
|---|---|
| T1 | Imprint forgery under C2, six core schemes, 10 cover images per scheme |
| T2 | Extended schemes that pass the inclusion rule, taken through F1 to F3 and T1 |
| T3 | Larger samples: 25 cover images per imprint cell; 200 images for the other measurements |
| T4 | Reprompting under C1 and C2 |

**Stretch.** Attempted only after the target items, and reported as future work otherwise.

| # | Work |
|---|---|
| S1 | Reprompting under C3 |
| S2 | UnMarker on Tree-Ring and Gaussian Shading |
| S3 | Imprint forgery under C3; surrogate-adversarial attack |

The floor covers each thing the proposal promised to report: a false-attribution rate by scheme and threshold, removal robustness alongside it, and the robustness-versus-forgeability comparison. Transfer across attacker models starts at T1.

## 4. Data sources

No training data is used. All data is either generated or read-only evaluation input.

| Source | Use | Access |
|---|---|---|
| Stable-Diffusion-Prompts, eval split | Prompts for generated images | Bundled with MarkDiffusion (`dataset/stable_diffusion_prompts`) |
| MS-COCO val2017 images | Real photographs: cover images for forgery and negatives for the real-photo baseline | `images.cocodataset.org` |
| SD 2.1-base weights | Target model; attacker model in C1 | `Manojb/stable-diffusion-2-1-base` on Hugging Face, pinned by commit hash |
| SD 1.5 weights | Attacker model in C2 | `stable-diffusion-v1-5/stable-diffusion-v1-5`, pinned by commit hash |
| PixArt-Σ weights | Attacker model in C3 | `PixArt-alpha/PixArt-Sigma-XL-2-512-MS`, pinned by commit hash |

Image and prompt subsets are chosen by a fixed seed and the selected identifiers are committed, so every run uses the same items. No dataset files or model weights are committed to the repository.

Findings from a first inspection of the bundled files (2026-10-01):

- The prompt eval split holds 8,192 prompts, 8,036 of them unique. Prompt length ranges from 1 to 258 words with a median of 36. Long prompts exceed the text encoder's 77-token limit and are truncated at generation.
- MarkDiffusion's bundled `dataset/mscoco/mscoco.parquet` contains no images. It is an index of 591,753 caption rows over 118,287 train2017 image URLs. The project therefore fetches val2017 photographs directly from COCO hosting.
- Default detector thresholds are not comparable across schemes. PRC's default configuration targets a false-positive rate of 1e-9 and GaussMarker's 1e-6, while Tree-Ring's carries a distance threshold and a p-value of 0.01. This is why every rate is also reported at a common calibrated operating point (section 5).

## 5. Metrics and statistics

**False-attribution rate.** The fraction of attacker-produced images that the detector flags as watermarked, where none of those images was generated by the provider.

- For imprint forgery, the images are real cover photographs after the imprint. The rate is reported next to the real-photo baseline: the fraction of the same photographs flagged before any attack.
- For reprompting, the images are ones the attacker regenerates from a reference image's inverted latent with a different prompt. Attacker prompts come from the same eval split and are disjoint from the reference prompts.

**Removal robustness.** The fraction of watermarked images still detected after each removal attack.

**Clean detection.** True-positive rate on watermarked generations and false-positive rate on unwatermarked generations from the same prompt set.

**Perceptual cost.** PSNR, SSIM, and LPIPS between each cover image and its forged version.

**Detector thresholds.** Every rate is reported at two operating points:

1. The toolkit's default threshold for the scheme.
2. A threshold calibrated to a 1% false-positive rate on 200 clean unwatermarked generations. With 200 negatives the false-positive rate resolves only in 0.5% steps, so no lower operating point is claimed.

**Attack budget.** Imprint runs continue to a fixed step cap with the detector evaluated every 10 steps. Success is reported at fixed step budgets, so the attacker is not assumed to have access to the detector. The cap is set once, after check-in 1, from the measured cost per step.

**Uncertainty.** Rates carry 95% Wilson intervals. Continuous metrics carry 95% percentile bootstrap intervals from 10,000 resamples over images. At 10 images per cell the intervals are wide: 10 successes out of 10 gives a lower bound near 72%, and 0 out of 10 gives an upper bound near 28%. That is enough to separate schemes that are forgeable from schemes that resist, and not enough to rank schemes that fall in between; the report says so.

## 6. Compute

| Resource | Role |
|---|---|
| Colab Pro | Development, check-in 1, and the floor |
| CoE HPC, P100 partition | Target and stretch items, if access is granted |

The floor is sized to finish on a single Colab Pro account. Its largest cost is F2: 60 imprint runs. The reference implementation's documentation implies roughly 16 seconds per optimization step on an A40; that is an estimate, not a measurement, and check-in 1 measures the real figure on Colab before any floor run is scheduled. If the measured cost puts F2 out of reach, the step cap is lowered before the cover count is.

The imprint optimization runs in fp32 with gradient checkpointing, as in the reference implementation. Whether it fits a 16 GB P100 is unverified and is checked before any HPC run is scheduled.

Sample sizes for each item are fixed before that item runs and are not changed after its results are seen.

## 7. Software design

| Path | Purpose |
|---|---|
| `src/wmforge/harness.py` | Generate watermarked and unwatermarked images and run detection through MarkDiffusion |
| `src/wmforge/imprint.py` | Imprint forgery: takes a cover image, a watermarked reference, and an attacker pipeline; returns the forged image and per-step records |
| `src/wmforge/metrics.py` | Rates, Wilson intervals, bootstrap intervals, perceptual metrics |
| `src/wmforge/data.py` | Seeded selection of prompts and cover images; cover download, crop, and resize |
| `src/wmforge/records.py` | Append-only CSV run log that resumes after an interrupted run |
| `src/wmforge/smoke.py` | Check-in 1 experiment runner (clean baseline, real-photo baseline, imprint forgery) |
| `src/wmforge/report.py` | Summary table and figures from a run log |
| `scripts/select_data.py` | Writes the committed prompt and image-identifier subsets |
| `tests/` | Unit tests; everything except the GPU run is tested locally |
| `notebooks/01_smoke_colab.ipynb` | Check-in 1 experiment, runnable on Colab |
| `results/checkin1/` | Result CSV, figures, image grid |
| `data/README.md` | Data sources and fetch steps |
| `docs/project-spec.md` | This document |
| `docs/checkin-1.md` | Data exploration and first results |

The harness and the attack communicate only through images: the harness produces a reference image, the attack returns a forged image, the harness returns a verdict. Neither depends on the other's internals, so a new scheme or a new attack is added without changing the other side.

Each run writes one CSV row per (scheme, attack, condition, image, step) with the detector score, verdict, perceptual metrics, wall-clock seconds, seed, and model commit hashes.

## 8. Check-in 1 milestone

A small end-to-end run on Colab that exercises every component and produces the first false-attribution number.

| Step | What | Size |
|---|---|---|
| 1 | Clean baseline for Tree-Ring and Gaussian Shading: true-positive and false-positive rates | 50 prompts per scheme |
| 2 | Real-photo baseline: detector on untouched COCO photographs | 50 photographs per scheme |
| 3 | Imprint forgery under C1 | 5 cover images per scheme |

For this run only, an imprint run stops at the first successful detection, with a cap of 60 steps, to limit compute. The check-in document labels the result accordingly, since stopping on the detector's verdict differs from the fixed-budget protocol in section 5.

Outputs: the result CSV; a table of rates; a plot of detector score against optimization step with the threshold marked; a grid of cover, forged, and difference images; measured seconds per imprint step.

If the forgery step cannot be made to run in time, step 1 is widened to the six core schemes and the check-in reports the clean baseline alone.

How the check-in requirements are met:

| Requirement | Where |
|---|---|
| Finalized specifications after feedback | This document, sections 1 to 10 |
| Tentative abstract (recommended) | Section 11 |
| Report outline (recommended) | Section 12 |
| Data sources identified and exploration started (required) | Section 4; `docs/checkin-1.md`; the notebook and `results/checkin1/` |
| Repository created, instructor and TA invited (required) | `github.com/yashashav-dk/cmpe261-watermark-forgery`; invitations sent before submission |
| Initial draft of the final report (recommended) | Sections 11 and 12 together with `docs/checkin-1.md` |

## 9. Risks

| Risk | Response |
|---|---|
| Imprint forgery costs more per image than estimated | Measured at check-in 1; step cap lowered first, then cover count |
| HPC access is not granted or arrives late | The floor needs only Colab Pro |
| Colab quota runs out (one Colab Pro account is available) | Runs are resumable from the CSV and continue when quota renews, on HPC if access is granted, or on free-tier Colab for generation and detection; the imprint step cap is lowered before the cover count |
| A core scheme fails the inclusion rule | Reported as excluded; the floor holds with the remaining schemes, and Tree-Ring and Gaussian Shading are implemented in both codebases |
| An extended scheme needs training or does not fit in memory | It stays out; the extended group is a target item, not a floor item |
| Package conflicts between MarkDiffusion and the reference attack code | The attack is re-implemented in this repository against MarkDiffusion's dependency set, so only one environment is needed |

## 10. Reproducibility, licensing, and roles

- Python and package versions are pinned in the repository; model weights are pinned by commit hash.
- All random seeds are fixed and recorded per row.
- The repository is licensed GPL-3.0, because the imprint attack is adapted from a GPL-3.0 codebase. MarkDiffusion is Apache-2.0, which is compatible.

| Member | Responsibility |
|---|---|
| Kanaka Sarat Siripurapu | Metrics, statistics, and provenance layer |
| Latha Boralingaiah | Attack implementation and transferability |
| Yashashav Devalapalli Kamalraj | Generation harness and environment |

## 11. Tentative abstract

Semantic watermarks embed a signal in the initial latent of a diffusion model and verify it by inversion. They are robust to common image distortions and are evaluated almost entirely against removal. Forgery is the more damaging failure: if an attacker can make an innocent photograph verify as watermarked, the watermark attributes content to a provider that never produced it. A black-box attack published at CVPR 2025 forged Tree-Ring and Gaussian Shading watermarks from a single reference image, but covered only those two schemes. We extend the MarkDiffusion toolkit with that forgery attack and benchmark up to nine semantic image watermarking schemes on Stable Diffusion 2.1-base. For each scheme we report the false-attribution rate, the fraction of real photographs that verify as watermarked after attack, at two detector operating points, for an attacker who uses the provider's model and for one who uses a different model. We report removal robustness alongside, to test whether schemes that resist removal are easier to forge. All experiments are inference-only, and all rates are reported with confidence intervals.

## 12. Report outline

1. **Introduction.** Removal versus forgery; why false attribution matters; regulatory context; contributions.
2. **Background and related work.** Semantic watermarking and inversion-based detection; the schemes studied; removal attacks; forgery attacks; existing benchmarks and their attack coverage.
3. **Threat model.** Attacker knowledge and resources; what counts as a successful forgery; the attacker-model conditions.
4. **Benchmark design.** Attacks added to MarkDiffusion; scheme inclusion rule; metrics; detector operating points; attack budgets.
5. **Experimental setup.** Models, data, sample sizes, statistics, compute.
6. **Results.**
   1. Clean detection baseline
   2. False attribution by scheme and threshold
   3. Transfer across attacker models
   4. Removal robustness versus forgeability
   5. Perceptual cost of forgery
7. **Discussion.** Which design properties track forgery resistance; implications for provenance systems; limitations, including sample size and items not completed.
8. **Conclusion and future work.**
9. **References.**
10. **Appendix.** Scheme configurations, per-scheme results, excluded schemes, reproducibility details.

## 13. Open items

- Survey whether any scheme beyond Tree-Ring and Gaussian Shading has a published forgery evaluation, including claims in the schemes' own papers. The proposal's statement that most schemes are untested rests on [1] covering two schemes; it has not been checked against later work.
- Re-verify the application date and scope of EU AI Act Article 50 against the current consolidated text before the final report.
- Locate an official UnMarker implementation and check its license before S2 is attempted.
- Define the surrogate-adversarial attack (which surrogate detector, which perturbation budget) before S3 is attempted.
- Confirm that the imprint optimization fits the P100's 16 GB.
- Confirm CoE HPC access.

## References

[1] A. Müller, D. Lukovnikov, J. Thietke, A. Fischer, E. Quiring. Black-Box Forgery Attacks on Semantic Watermarks for Diffusion Models. CVPR 2025. arXiv:2412.03283. Code: github.com/and-mill/semantic-forgery.

[2] L. Pan et al. MarkDiffusion: An Open-Source Toolkit for Generative Watermarking of Latent Diffusion Models. arXiv:2509.10569. Code: github.com/THU-BPM/MarkDiffusion.

[3] A. Kassis, U. Hengartner. UnMarker: A Universal Attack on Defensive Image Watermarking. IEEE S&P 2025. arXiv:2405.08363.
