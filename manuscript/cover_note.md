# IEEE BIBM 2026 Doctoral Forum, paper S60204: camera-ready note

Dear Dr. Yi He and Dr. Xingquan Zhu,

Thank you for the acceptance and for the two reviews. The camera-ready version is the accepted manuscript with the reviewers' requests addressed and three factual corrections. The title now matches the portal record ("Spiking Reservoir", without the hyphen). Author names, affiliations, and order are unchanged.

## Response to the reviews

| Review point | Change in the camera-ready |
|---|---|
| R1-W1: the title's central concept (spectral radius) was never tested; Fig. 2c was true by construction and Fig. 2d was label-free; BSC₁ ≈ BSC₆ suggested the dynamics may not contribute | Reviewed Fig. 2c and 2d (now Fig. 1c and 1d) are replaced by a spectral-radius sweep (ρ ∈ {0, 0.3, 0.6, 0.9, 1.2, 1.5}) with a no-recurrence ablation and a label-free damage-spreading order parameter. Removing the recurrence costs 0.049 BA (95% CI [−0.098, −0.002]); the half-maximum crossing of the damage curve is ρ* ≈ 0.82, next to the pre-specified 0.9, inside a broad optimum (Sec. V-A, Fig. 1). Normalized by the rate-matched reference 2r(1−r), the damage does not die out below ρ*, so the paper reads ρ* as the onset of recurrence-driven firing rather than as a first spreading of damage. The BSC₁ control is now reported as a paired difference (+0.001, CI includes zero) and the text claims no temporal-coding benefit. |
| R1-W2: situate the four non-learned fills within the neuroimaging missing-data spectrum, including the two suggested references | Related Work (Sec. II) now places the fills on the spectrum from constant fills and spherical-spline interpolation, through learned imputation and spatial filtering, to generative synthesis (ViT-GAN, latent diffusion), citing both suggested papers; the Discussion draws the implication for learned imputers. |
| R2-1: perturbations were applied at different levels across models | A signal-level experiment corrupts the raw signal identically for every encoder, including EEGNet, with shared draws per fold (electrode removal 10/30/50%, 5 dB noise, ±50 ms jitter; Sec. V-C, Table III). The feature-coordinate experiment is kept, since the fill-rule effect is by nature feature-level, and is labeled as such. |
| R2-2: train-only PCA throughout | The reservoir's PCA basis is fit on the training subjects of each fold in every analysis; the pooled basis is reported only as a sensitivity check (0.485 vs 0.487). |
| R2-3: how dependence across repeated folds is handled | Out-of-fold probabilities are pooled across the five partitions into one prediction per observation, and all intervals and paired comparisons come from a bootstrap over the 211 subjects (4000 resamples), so no test treats folds as independent (Sec. IV-B). Fold-level p-values are replaced by paired subject-level CIs. |
| R2-4: the edge-of-stability interpretation needed justification; no transition at ρ = 1 | ρ = 1 is now named as the echo-state heuristic for rate reservoirs rather than a stability bound; the crossing is measured, not assumed, and lies at ρ* ≈ 0.82; a one-step branching bound (Sec. III-B) shows that where damage can first spread depends on the membrane density at threshold and the column norm of W, not on the unit circle. |

## Theory added at the author's request

Three short theoretical statements now accompany the measurements; none changes a reported number.

1. Proposition 1 (Sec. III-E) states and proves that zero-fill scoring is not invariant to an information-preserving re-centering of the features, while mean and kNN fills are, with the linear-readout bound on how far the two fills can disagree. This is the mechanism behind the fill-rule effect that R1-W2 and R2-1 asked to be situated and controlled.
2. Proposition 2 (Sec. III-E) gives the chance floor of raw retention and the first-order sampling error of above-chance retention, which is why absolute BA and paired subject-level differences are primary (R2-3).
3. A one-step branching bound (Sec. III-B) gives where a thresholded LIF reservoir's damage can first spread, rho_c ~ 1/(p_theta * kappa-bar), with kappa-bar = 13.4 computed from the committed seed-42 weights. It shows why that threshold need not sit at rho = 1 (R2-4). Checking it against the measured curve led to a corrected reading of rho*: relative to the rate-matched reference the damage never dies out below rho*, and the mean firing rate doubles across it, so rho* is reported as a rate-associated crossover of the damage statistic (its half-maximum crossing), not as the branching threshold and not as a measured transition between ordered and chaotic dynamics. Equating rho_c with rho* would require a membrane density at threshold of about 0.09 per unit potential, which the paper states as a refutable condition and does not test; the long-lag damage itself does not bound p_theta, because a sub-threshold difference decays with time constant 1/beta = 20 steps absent intervening spikes or resets, so damage can persist with a one-step count below one.

## Consistency correction after the camera-ready review

A final pass aligned every statement about the reservoir's dynamics with what the damage experiment measures. No reported number changed.

1. Abstract, contribution 4, Sec. III-B, the Fig. 1 caption, Sec. V-A, the Discussion and the Conclusion now describe rho* as the half-maximum crossing of the damage curve, a rate-associated crossover, and no longer as a measured edge or transition; the accepted title is retained.
2. Fig. 1(d) no longer carries "ordered" and "irregular" regime labels or regime shading; a dashed line marks rho* and the panel title reads "crossover". The panel is regenerated from `outputs/aggregate/e1_rho_sweep.json` by the patched `analysis/make_fig_reservoir_dynamics.py` and spliced into the committed PDF by `analysis/splice_fig_reservoir_dyn_panel_d.py` (panels a and b need the restricted pickle); running the figure script locally regenerates the complete figure with the same panel (d).
3. The inference from long-lag damage at rho = 0.3 to a one-step count above one, and the resulting bound p_theta >~ 0.25, is withdrawn (item 3 above); the branching threshold is stated as undetermined until p_theta is measured.
4. The BSC6 versus BSC1 comparison reports the paired difference and interval (+0.001 BA, 95% CI [−0.044, +0.047]) as no detected advantage, without declaring equivalence.
5. Sec. IV-B states that the subject-bootstrap intervals are conditional on the sampled electrode masks (one draw per seed and fold), the fitted models, and the single reservoir weight draw.
6. Sec. V-D is retitled "External Check of the Fill-Rule Effect", matching what the DEAP experiment tests.

To keep the body on six pages, Figs. 1 to 4 are printed 2 to 7% narrower (smallest printed text about 5.3 pt in Figs. 3 and 4, 5.5 pt or larger elsewhere) and a few sentences in Related Work, Sec. V-C, Sec. V-D, the Discussion, the Limitations and the Ethics statement were shortened without changing their content.

To keep the body within six pages, the kNN and spatial per-encoder point values at 30% dropout are now carried by the paired differences in Sec. V-B rather than listed separately, and a few sentences that duplicated Methods statements were removed. The four figures are printed at sizes that keep their smallest text at or above 5.5 pt.

## Corrections independent of the reviews

1. Epoch timing. The analyzed 256-sample array spans −200 to +800 ms around onset (every fourth sample of the raw 1024 Hz epoch, z-scored per epoch), not 256 post-stimulus samples. The dataset description, the reservoir window (about −160 to +73 ms), the ERP-window labels (about −120 to 0, 50 to 250, 250 to 600 ms) and the ERP figure's time axis (reviewed Fig. 3, now Fig. 2) are corrected. No number changes.
2. The LIF update equations now state the implemented recurrence exactly (leak (1−β), multiplicative reset, rectification at zero).
3. The Banville et al. (2022) reference (reviewed [21], camera-ready [23]) is corrected to NeuroImage 251:118994.

## Values that changed from the reviewed version, and why

The reviewers' requests R2-1 through R2-3 change the estimator (subject-level intervals on pooled predictions), the reservoir's PCA protocol, and the perturbation protocol, and every reported value was recomputed from committed, verified code. The band-power features are recomputed from the analyzed signal with the documented Welch estimator. The changes a reader of the reviewed version will notice:

| Quantity | Reviewed | Camera-ready | Reason |
|---|---|---|---|
| Clean BA: EEGNet / ERP-window / band-power / reservoir | 0.711 / 0.616 / 0.485 / 0.463 | 0.731 / 0.629 / 0.494 / 0.487 | subject-level estimator on pooled predictions (R2-3); train-only PCA (R2-2); band power recomputed |
| 30% dropout, zero-fill: ERP-window / band-power / reservoir | 0.454 / 0.408 / 0.456 | 0.536 / 0.417 / 0.487 | same, with the dropout analysis rerun under the committed protocol |
| 30% dropout, mean-fill: ERP-window / band-power / reservoir | 0.489 / 0.431 / 0.461 | 0.578 / 0.472 / 0.487 | same |
| EEGNet at 30% removal, without / with augmentation | 0.554 / 0.674 | 0.660 / 0.703 | signal-level protocol shared with every encoder (R2-1) |
| Amplitude-noise result | feature-level noise lowered ERP-window to 0.461 | signal-level 5 dB noise leaves ERP-window and the reservoir within noise of clean; band-power loses 0.059 | noise is now applied to the signal, as R2-1 requested; the feature-level result and the dimensionality-matched random-projection control that depended on it are withdrawn |
| Headline fill-rule claim | corrected imputation changes the fixed-encoder ranking (ERP-window overtakes the reservoir) | ERP-window leads the reservoir under every fill; zero-fill halves the measured lead (+0.049 vs +0.092 to +0.107 BA, paired CIs) | follows from the recomputed values |
| DEAP values | unchanged | unchanged (reproduced to 1e-4) | |
| Input-level jitter check | reservoir more sensitive to jitter (0.422) | ±50 ms signal-level jitter moves no fixed encoder (reservoir 0.493) | jitter re-measured under the shared signal-level protocol (R2-1); the earlier feature-level check is withdrawn |
| Above-chance retention | presented as the more comparable summary | reported as a secondary diagnostic; Proposition 2 gives its chance floor and sampling error | subject-level inference (R2-3) |
| Permutation null | 100 permutations, BA 0.338 ± 0.022 | 20 within-subject permutations, mean BA 0.33 to 0.34 | recomputed under the committed protocol |
| Table I macro-F1 and AUC for EEGNet and BSC1 | reported | BA only; BSC1 moved into the text | only committed outputs are reported, and the committed EEGNet and BSC1 runs export BA |

The pipeline schematic (reviewed Fig. 1) is removed to keep the body within six pages after the additions above; the remaining figures are printed at sizes that keep their smallest text at or above 5.5 pt.

Sincerely,

Andrew Lane
