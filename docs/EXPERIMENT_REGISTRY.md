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

None.
