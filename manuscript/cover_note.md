# IEEE BIBM 2026 Doctoral Forum, paper S60204: camera-ready note

Dear Dr. Yi He and Dr. Xingquan Zhu,

Thank you for the acceptance and for the two reviews. The camera-ready version is the accepted manuscript with the reviewers' requests addressed and three factual corrections. The title now matches the portal record ("Spiking Reservoir", without the hyphen). Author names, affiliations, and order are unchanged.

## Response to the reviews

| Review point | Change in the camera-ready |
|---|---|
| R1-W1: the title's central concept (spectral radius) was never tested; Fig. 2c was true by construction and Fig. 2d was label-free; BSC₁ ≈ BSC₆ suggested the dynamics may not contribute | Reviewed Fig. 2c and 2d (now Fig. 1c and 1d) are replaced by a spectral-radius sweep (ρ ∈ {0, 0.3, 0.6, 0.9, 1.2, 1.5}) with a no-recurrence ablation and a label-free damage-spreading order parameter. Removing the recurrence costs 0.049 BA (95% CI [−0.098, −0.002]); the measured transition is ρ* ≈ 0.82, next to the pre-specified 0.9, inside a broad optimum (Sec. V-A, Fig. 1). The BSC₁ control is now reported as a paired difference (+0.001, CI includes zero) and the text claims no temporal-coding benefit. |
| R1-W2: situate the four non-learned fills within the neuroimaging missing-data spectrum, including the two suggested references | Related Work (Sec. II) now places the fills on the spectrum from constant fills and spherical-spline interpolation, through learned imputation and spatial filtering, to generative synthesis (ViT-GAN, latent diffusion), citing both suggested papers; the Discussion draws the implication for learned imputers. |
| R2-1: perturbations were applied at different levels across models | A signal-level experiment corrupts the raw signal identically for every encoder, including EEGNet, with shared draws per fold (electrode removal 10/30/50%, 5 dB noise, ±50 ms jitter; Sec. V-C, Table III). The feature-coordinate experiment is kept, since the fill-rule effect is by nature feature-level, and is labeled as such. |
| R2-2: train-only PCA throughout | The reservoir's PCA basis is fit on the training subjects of each fold in every analysis; the pooled basis is reported only as a sensitivity check (0.485 vs 0.487). |
| R2-3: how dependence across repeated folds is handled | Out-of-fold probabilities are pooled across the five partitions into one prediction per observation, and all intervals and paired comparisons come from a bootstrap over the 211 subjects (4000 resamples), so no test treats folds as independent (Sec. IV-B). Fold-level p-values are replaced by paired subject-level CIs. |
| R2-4: the edge-of-stability interpretation needed justification; no transition at ρ = 1 | ρ = 1 is now named as the echo-state heuristic for rate reservoirs rather than a stability bound; the transition is measured, not assumed, and lies at ρ* ≈ 0.82. |

## Corrections independent of the reviews

1. Epoch timing. The analyzed 256-sample array spans −200 to +800 ms around onset (every fourth sample of the raw 1024 Hz epoch, z-scored per epoch), not 256 post-stimulus samples. The dataset description, the reservoir window (about −160 to +73 ms), the ERP-window labels (about −120 to 0, 50 to 250, 250 to 600 ms) and the ERP figure's time axis (reviewed Fig. 3, now Fig. 2) are corrected. No number changes.
2. The LIF update equations now state the implemented recurrence exactly (leak (1−β), multiplicative reset, rectification at zero).
3. Reference [23] (Banville et al., 2022) is corrected to NeuroImage 251:118994.

## Values that changed from the reviewed version, and why

The reviewers' requests R2-1 through R2-3 change the estimator (subject-level intervals on pooled predictions), the reservoir's PCA protocol, and the perturbation protocol, and every reported value was recomputed from committed, audited code. The band-power features are recomputed from the analyzed signal with the documented Welch estimator. The changes a reader of the reviewed version will notice:

| Quantity | Reviewed | Camera-ready | Reason |
|---|---|---|---|
| Clean BA: EEGNet / ERP-window / band-power / reservoir | 0.711 / 0.616 / 0.485 / 0.463 | 0.731 / 0.629 / 0.494 / 0.487 | subject-level estimator on pooled predictions (R2-3); train-only PCA (R2-2); band power recomputed |
| 30% dropout, zero-fill: ERP-window / band-power / reservoir | 0.454 / 0.408 / 0.456 | 0.536 / 0.417 / 0.487 | same, with the dropout analysis rerun under the committed protocol |
| 30% dropout, mean-fill: ERP-window / band-power / reservoir | 0.489 / 0.431 / 0.461 | 0.578 / 0.472 / 0.487 | same |
| EEGNet at 30% removal, without / with augmentation | 0.554 / 0.674 | 0.660 / 0.703 | signal-level protocol shared with every encoder (R2-1) |
| Amplitude-noise result | feature-level noise lowered ERP-window to 0.461 | signal-level 5 dB noise leaves ERP-window and the reservoir within noise of clean; band-power loses 0.059 | noise is now applied to the signal, as R2-1 requested; the feature-level result and the dimensionality-matched random-projection control that depended on it are withdrawn |
| Headline fill-rule claim | corrected imputation changes the fixed-encoder ranking (ERP-window overtakes the reservoir) | ERP-window leads the reservoir under every fill; zero-fill halves the measured lead (+0.049 vs +0.092 to +0.107 BA, paired CIs) | follows from the recomputed values |
| DEAP values | unchanged | unchanged (reproduced to 1e-4) | |

The pipeline schematic (reviewed Fig. 1) is removed to keep the body within six pages after the additions above.

Sincerely,

Andrew Lane
