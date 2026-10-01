# Camera-ready code audit (2026-10-01)

Scope: every script that produces a number, table, or figure in
`manuscript/main_bibm2026.tex`, the methods text that describes them, and the
research harness installed from the audit repository. Paper: BIBM 2026 Doctoral
Forum S60204 (accepted), camera-ready revision.

## 1. Harness (audit repository) sync

- Installed harness compared file by file with
  `TheAwesomeAndy/myResearchAssitantHarness@b549c07`: `papercheck/` 20/20,
  `.claude/` 20/20, `tools/`, `makefiles/`, `playbooks/`, and all 19 harness
  scripts byte-identical. Differences: `harness/papercheck.toml` (project
  configuration) and `harness/memory/memory.jsonl` (project state), both expected.
- Harness self-tests: unit tests 140/140 pass; fixture suite 69/70.
- **Bug found and fixed (`scripts/verify_latex.py`):** latexmk/pdflatex ran with
  `cwd` set to the manuscript's directory but received the caller-relative path, so
  any manuscript in a subdirectory (including this repo's
  `manuscript/main_bibm2026.tex` and the harness's own `good_latex_build` fixture)
  could not be built by the harness's LaTeX gate or its `make` target. The fix
  passes the bare file name. After the fix: fixtures 70/70, unit tests 140/140, and
  the gate builds this manuscript. The same fix should be applied upstream.

## 2. Analysis code against the paper

| # | Finding | Severity | Resolution |
|---|---|---|---|
| A1 | Reservoir code (`regen_reservoir_embedding.py`, `experiment2_rawsignal.py`) is an exact replica of the upstream source (`dissoAdventureExperiments/experiments/ch5_4class/ch5_4class_01_feature_extraction.py`): leak `(1-β)`, multiplicative reset, subtract-θ, floor at 0, Xavier-uniform init (seed 42), ρ = 0.9, BSC6 over t ∈ [10, 70), PCA-64 shared across electrodes. | — | verified |
| A2 | The paper's LIF equations did not match the code: Eq. 2 used `β v_t` (5% retention for β = 0.05; the code retains 95%), and omitted the reset factor and the rectification at zero. | error in text | Eqs. 2–3 rewritten to the exact update the code implements. |
| A3 | Band power: the pickle's `conv_feats` (used for the published Tables I and III) cannot be reproduced from the analysed signal `X_ds` with the documented estimator (Welch, nperseg 256, 1–4/4–8/8–13/13–30/30–45 Hz, trapezoid). Median ratio 6.6, band-dependent (≈4× delta to ≈21× beta), so a different signal or preprocessing was used upstream; the upstream code itself computes band power on `X_ds`. Table IV already recomputed band power from `X_ds`, so the paper used two different "band-power" encoders under one name. | inconsistency | Band power is now recomputed from `X_ds` with the documented estimator everywhere. |
| A4 | Published Tables I, III, IV match their source JSON cell for cell. | — | verified |
| A5 | No committed script for `controls_*.json` (permutation null, PCA component count, amplitude-noise controls), `eegnet*.json`, `deap_replication.json`, or for Figs. 2 and 4. | reproducibility gap | Replaced by committed scripts (E3–E6, `make_fig_erp.py`, `make_fig_deap_aug.py`); the old JSON files are kept for provenance only. |
| A6 | Methods described a dimensionality-matched random-projection control and temporal jitter, but no result for either was reported. | text/result mismatch | Random-projection sentence removed; jitter now measured (E4, E3). |
| A7 | Methods stated "BA and macro-F1", but only BA was reported. | text/result mismatch | Table I reports BA, macro-F1 and macro one-vs-rest AUC (E5). |
| A8 | Feature-level perturbations for the fixed encoders vs input-level for EEGNet (reviewer R2.1). | design | One signal-level protocol with shared draws for every encoder (`perturbations.py`, E3, E4). |
| A9 | Pooled (transductive) PCA in the main results (reviewer R2.2). | design | Train-only PCA in every main analysis; pooled PCA kept as a sensitivity check. |
| A10 | Training-set reservoir codes in `experiment2_rawsignal.py` were embedded with `PCA.fit_transform`, test codes with `PCA.transform`; with the randomized SVD solver these differ slightly (clean reservoir BA 0.480 vs 0.487 with `transform` for both). | minor inconsistency | E4 embeds train and test with `transform`. |
| A11 | Proposition 1 called the reservoir code "mean-centered (μ = 0)". With a PCA basis shared across electrodes only the pooled mean is zero; per-feature means are near zero. | overstatement | Text says near-centered; the measured mean \|μ\|/σ per encoder is reported (E5). |
| A12 | "BSC₁ matches BSC₆ within the subject-level interval" had no subject-level computation behind it. | unsupported claim | Computed at subject level (E5). |
| A13 | Author wording rules (memory journal #16) were violated in 9 places in the July text. | style rule | Fixed; `analysis/check_author_wording.py` now enforces them. |
| A14 | One-fold check that the feature-coordinate fill is applied (reservoir, ρ = 0.9): 37/129 (zero) and 38/129 (mean) test predictions change; mean \|Δlogit\| ≈ 0.87 vs mean \|logit\| ≈ 1.69. Aggregate BA nonetheless barely moves because each observation is scored under five partitions with different dropped electrodes. | — | verified, not a bug |

## 3. Reproduction checks (current library versions: numpy 2.4.6, scikit-learn 1.9.1)

| Anchor | Published | Reproduced |
|---|---|---|
| Pooled-PCA reservoir clean BA, per-fold mean (`regen_reservoir_embedding.py`) | 0.4626 | 0.4626 |
| Signal-level 30% removal, reservoir, train-fold PCA | 0.474 | 0.474 (E1, ρ = 0.9) |
| DEAP band-power clean | 0.639 | 0.6390 |
| DEAP 10% removed, zero fill | 0.581 | 0.5808 |
| DEAP 30% zero / mean / kNN | 0.540 / 0.621 / 0.638 | 0.5397 / 0.6207 / 0.6381 |
| All ten DEAP values (clean; 10/30/50% × zero/mean/kNN) vs the uncommitted original run | — | max \|difference\| 4.8e-05 (storage rounding) |
| Feature-coordinate ERP-window at 30% (zero / mean / kNN / spatial) | 0.536 / 0.578 / 0.610 / 0.589 | PENDING (E2) |

## 4. Gates now in place

- `python analysis/check_author_wording.py` — author wording rules.
- `python scripts/check_table_manifest.py harness/table_manifest.yaml` — every
  table cell in the paper against `outputs/aggregate/paper_values.csv`
  (written by `analysis/export_paper_values.py`).
- `python scripts/verify_latex.py manuscript/main_bibm2026.tex` — build (fixed).
- `python -m papercheck manuscript/main_bibm2026.tex` — harness quality gates.
