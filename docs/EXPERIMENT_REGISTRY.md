# Experiment registry

One row per experiment: what it is, how to run it, what it writes, and whether
it belongs to the accepted paper. `analysis/README.md` remains the
authoritative map from paper element to script. This file adds status and the
rules for adding experiments.

## Status values

- **accepted**: produces a number, table, or figure in the accepted paper. Frozen (`docs/BASELINE.md`).
- **sensitivity**: reported in the paper as a check, not a main result. Frozen.
- **superseded**: output kept for provenance; the paper does not depend on it.
- **legacy**: output with no committed generating script.
- **extension**: created after acceptance. None exist yet.

## Shared protocol (all SHAPE experiments)

`StratifiedGroupKFold(5, shuffle=True)`, seeds 42, 43, 44, 45, 46, subject IDs
as groups, train-only `StandardScaler`, `LogisticRegression(C=1.0,
class_weight="balanced", solver="lbfgs", max_iter=2000, random_state=seed)`,
out-of-fold probabilities summed over partitions, subject-level bootstrap with
4000 resamples. Reservoir: N=256, beta=0.05, theta=0.5, weight seed 42, BSC6
over samples [10, 70), PCA-64 with `random_state=42`.

Perturbation draws: `default_rng(1000*seed + fold)` for electrode removal,
offset 10000 for noise, offset 20000 for jitter (`analysis/perturbations.py`).

## Accepted and sensitivity experiments

| ID | Purpose | Command | Key parameters | Output | Paper element | Status |
|---|---|---|---|---|---|---|
| E1 | Spectral-radius sweep, rho = 0 ablation, damage spreading | `python analysis/experiment_camera_ready.py e1` | rho grid 0, 0.3, 0.6, 0.9, 1.2, 1.5; fine grid 0 to 2.0 step 0.1; 400 drives, RNG seed 0, ten-step settling; 30% dropout focus | `e1_rho_sweep.json` | Fig. 1(c), 1(d); Sec. V-A | accepted |
| E2 | Feature-coordinate fills with train-only PCA | `python analysis/experiment_camera_ready.py e2` | fills zero, mean, knn, spatial; dropout 10 to 50%; rho 0.9 | `e2_trainonly_pca_fills.json` | Table II, Fig. 3 | accepted |
| E3 | EEGNet under signal-level conditions | `python analysis/experiment_eegnet_signal.py` | EEGNet-8,2; 80 epochs, batch 64, Adam lr 1e-3, dropout 0.25; torch seed `100*seed + fold`; 2 threads; removal 0, 10, 30, 50% | `e3_eegnet_signal.json` | Table III, Fig. 4(b) | accepted |
| E4 | Signal-level perturbations, fixed encoders | `python analysis/experiment_signal_perturbations.py` | removal 10, 30, 50%; 5 dB noise; plus or minus 50 ms jitter | `e4_signal_perturbations.json` | Table III | accepted |
| E5 | Controls: permutation null, PCA component count, BSC1, centeredness, clean metrics | `python analysis/experiment_controls.py` | 20 within-subject permutations, RNG seed 2026; K in 16, 32, 64, 128 | `e5_controls.json` | Table I; Sec. V-A; Fig. 3 legend | accepted |
| DEAP | External check of the fill-rule effect | `python analysis/deap_replication.py` | within-subject `StratifiedKFold(5)`, seeds 42 to 46; bands 4-8, 8-12, 12-30, 30-45 Hz, log mean PSD; removal 10, 30, 50% | `deap_replication_v2.json` | Fig. 4(a); Sec. V-D | accepted |
| S1 | Pooled (transductive) PCA sensitivity | `python analysis/regen_reservoir_embedding.py`, then `python analysis/reanalysis_subject_bootstrap.py` | pooled PCA-64; uses the pickle's `conv_feats` for band power | `subject_bootstrap_reanalysis.json` | Sec. V-A sensitivity statement | sensitivity |
| EXP | Paper-value export for the table gate | `python analysis/export_paper_values.py` | reads E2, E3, E4, E5 JSON | `paper_values.csv`, `harness/table_manifest.yaml` | Tables I to III | accepted (tooling) |

All output paths are under `outputs/aggregate/` unless shown otherwise. E1 to
E5 and S1 need the SHAPE pickle; DEAP needs the DEAP release. Run times are in
`analysis/README.md`.

Note on DEAP: it uses a within-subject protocol by design, stated in the
paper. It is not a deviation from the subject-grouped SHAPE protocol.

## Run record for the accepted experiments

Every accepted experiment was run by the author for the camera-ready, and its
output is committed. "Not re-run" elsewhere in these docs refers only to the
modernization sessions, which had no access to the restricted data. It never
means an experiment was not run.

| ID | Output committed | Evidence that it ran and reproduces (historical) | Tests in this repository |
|---|---|---|---|
| E1, E2, E4, E5 | 2026-10-01, PR #35 | `docs/CODE_AUDIT.md` section 3: anchors and cross-script identities | `tests/test_baseline_integrity.py`, `tests/test_manuscript_tables.py` |
| **E3 (EEGNet)** | `e3_eegnet_signal.json`, 2026-10-01, PR #35 | Audit section 3: a rerun gave every BA and paired value identical to the first run (CPU, fixed seeds, two threads). Audit A16: the run's imported perturbation module matched the committed one. An earlier run from June 2026 (PR #17) is kept as `eegnet.json` and `eegnet_aug.json`; it is the "submitted" column of `manuscript/cover_note.md` | `tests/test_eegnet_and_deap_outputs.py` (every EEGNet number in Tables I to III and the Training effect paragraph; shared draws with E4), `tests/test_eegnet_code.py` (architecture, augmentation, deterministic training; needs torch) |
| **DEAP** | `deap_replication_v2.json`, 2026-10-01, PR #35 | Audit section 3: all ten values reproduce the original run (`deap_replication.json`, July 2026, PR #22) to within 4.8e-05 | `tests/test_eegnet_and_deap_outputs.py` (audit anchors, the ten-value comparison, every number in Sec. V-D and the Fig. 4 caption), `tests/test_deap_code.py` (estimator, loader, fills, within-subject evaluation) |
| S1 | `subject_bootstrap_reanalysis.json` | Audit section 3: anchor 0.4626 reproduced | `tests/test_baseline_integrity.py` |

## Figures

| Figure | Script | Inputs | Needs restricted data |
|---|---|---|---|
| Fig. 1 `fig_reservoir_dyn.pdf` | `analysis/make_fig_reservoir_dynamics.py` | SHAPE pickle, `e1_rho_sweep.json` | yes (panels a, b) |
| Fig. 1 panel (d) only | `analysis/splice_fig_reservoir_dyn_panel_d.py` | `e1_rho_sweep.json`, committed PDF | no |
| Fig. 2 `fig_erp.pdf` | `analysis/make_fig_erp.py` | SHAPE pickle | yes |
| Fig. 2 raster resolution | `analysis/upsample_fig_erp_raster.py` | committed PDF | no |
| Fig. 3 `fig_impute_subj.pdf` | `analysis/make_fig_subject_level.py` | `e2_trainonly_pca_fills.json`, `e5_controls.json` | no |
| Fig. 4 `fig_deap_aug.pdf` | `analysis/make_fig_deap_aug.py` | `deap_replication_v2.json`, `e3_eegnet_signal.json` | no |

The committed figures are frozen. Do not regenerate them (`CLAUDE.md`, Figure
policy).

## Superseded and legacy outputs

| Output | Status | Note |
|---|---|---|
| `experiment2_rawsignal.json` | superseded | Script `analysis/experiment2_rawsignal.py` is committed and its functions are still imported. Replaced by E4 (`docs/CODE_AUDIT.md` A10) |
| `deap_replication.json` | legacy | Replaced by `deap_replication_v2.json` |
| `controls_extra.json`, `controls_impute.json`, `controls_impute2.json`, `controls_raw.json`, `controls_stats.json`, `controls_v2.json`, `controls_summary.csv` | legacy | No committed script (A5) |
| `eegnet.json`, `eegnet_aug.json` | legacy | No committed script; replaced by E3 |
| `phaseB_reproduction_summary.csv` | legacy | No committed script and no reference elsewhere in the repository |

Keep all of these. They are provenance.

## Adding an experiment after acceptance

Not yet exercised. The convention below was approved in the modernization
plan. No tooling enforces it yet, and the directories it names do not exist
until the first extension experiment creates them.

1. Give it an ID with the prefix `X` and a date, for example `X01-2026-12`.
   Do not reuse `E1` to `E5`.
2. Put the script under `experiments/<ID>/`. Import baseline code; do not edit
   the baseline scripts to accommodate the new experiment.
3. Write outputs under `outputs/extensions/<ID>/`. Never under
   `outputs/aggregate/`.
4. Each output carries a provenance block: experiment ID, git commit, UTC
   time, library versions, data file checksum, and the full parameter set.
5. Add a row to an "Extension experiments" table in this file with status
   `extension` and one of: `unverified`, `reproduced once`, `independently
   reproduced`.
6. Record the decision to run it, and its outcome, in the memory journal.
7. Protocol changes (for example leave-one-subject-out, a different seed set,
   classifier, or scaler) need explicit author approval first (`CLAUDE.md`,
   Validation protocol).

## Extension experiments

These are not part of the accepted paper. Verification status is one of:
`not run`, `unverified`, `reproduced once`, `independently reproduced`.

| ID | Question | Code | Output | Status |
|---|---|---|---|---|
| X01-2026-11 | Does the reservoir's balanced accuracy depend on the per-epoch z-scoring of its input? Four scalings (A epoch z-score, B pre-stimulus SD, C none, D post-stimulus z-score) by four encoders (R1 accepted reservoir, R2 the same reservoir stopped at stimulus onset, P pre-stimulus channel means, E ERP windows) under the accepted protocol, with a reproduction check against the paper's `X_ds` first and a within-subject permutation null | `experiments/X01-2026-11/run_x01.py` at commit `7532153`; needs `SHAPE_RAW_DIR` and `ARSPI_SHAPE_FEATURES` | `outputs/extensions/X01-2026-11/x01_scaling.json` | **run 2026-11-22 on the SHAPE data (211 subjects, 633 observations); reproduced once**: a second run from the same commit, on the same machine and in the same session, gave an output identical in every value. Not independently reproduced. See the summary below |

### X01-2026-11 summary (new result, not part of the accepted paper)

All values are from `outputs/extensions/X01-2026-11/x01_scaling.json`. Balanced
accuracy with subject-level 95% CI; chance is 0.333.

Step 0: the signal rebuilt from the raw epochs equals the paper's `X_ds`
(maximum absolute difference 0.0; subject order and labels match).

| Encoder | A epoch_z | B pre_sd | C none | D post_z |
|---|---|---|---|---|
| R1 reservoir_bibm | 0.487 [0.447, 0.523] | 0.294 [0.261, 0.325] | 0.316 [0.278, 0.354] | 0.464 [0.425, 0.502] |
| R2 reservoir_onset | 0.420 [0.384, 0.455] | 0.297 [0.264, 0.332] | 0.292 [0.258, 0.329] | 0.498 [0.463, 0.534] |
| P prestim_mean | 0.542 [0.507, 0.577] | 0.346 [0.313, 0.381] | 0.340 [0.303, 0.376] | 0.555 [0.518, 0.591] |
| E erp_windows | 0.629 [0.597, 0.660] | 0.510 [0.477, 0.543] | 0.545 [0.513, 0.577] | 0.632 [0.597, 0.667] |

Paired differences (A minus B, A minus C): R1 +0.193 [+0.139, +0.246] and
+0.171 [+0.122, +0.223]; R2 +0.124 [+0.076, +0.172] and +0.127 [+0.077, +0.177];
P +0.196 [+0.148, +0.242] and +0.203 [+0.153, +0.253]; E +0.119 [+0.076, +0.161]
and +0.084 [+0.044, +0.123].

Mean firing rate: R1 0.124, 0.129, 0.144, 0.136 and R2 0.122, 0.124, 0.138,
0.135 under A, B, C, D.

Permutation null for R1 under B (partition seed 42, 50 permutations): null mean
0.331, 2.5th to 97.5th percentile 0.293 to 0.369; observed 0.303.

What was observed, stated without interpretation beyond the numbers:

- The R1 and E values under A reproduce the accepted paper's 0.487
  [0.447, 0.523] and 0.629 [0.597, 0.660].
- The reservoir's accuracy depends on the scaling. Under B and C its interval
  contains chance, and under B the observed value lies inside the permutation
  null.
- Pre-stimulus channel means (P) and a reservoir that never receives a
  post-stimulus sample (R2) are above chance under A and D and at chance under
  B and C. A and D use post-stimulus samples to compute the scaling; B and C do
  not.
- Firing rates are similar across scalings, so the differences are not
  explained by a silent or saturated reservoir.

This result does not change the accepted paper, its outputs, or its figures.
It bears on the corrected-window question already listed in
`docs/RESEARCH_MAP.md` (audit A18). What it means for the paper's claims is the
author's decision.

