# Research map

Each scientific component of the accepted paper, where it is implemented, what
evidence supports it, and what tests guard it. Use this to find the
authoritative file before reading or changing anything.

Evidence classes used below (defined in `AGENTS.md`):
**[V]** verified in the session that wrote this file,
**[H]** historical finding recorded by an earlier audit and not re-run,
**[O]** open question.

Nothing in this file was re-run on the real data. Every numerical statement
about the paper is [H] and is quoted from `CLAUDE.md`, `docs/CODE_AUDIT.md`, or
the memory journal. The code locations are [V] by reading. The Tests column
names tests that pass on synthetic signals; they pin behavior and say nothing
about EEG.

## Central idea

A fixed LIF reservoir with BSC6 spike-bin encoding defines a
perturbation-characterized temporal measurement operator for affective EEG/ERP
observations. Scope rules are in `CLAUDE.md`. Lineage: this is the temporal
encoding stage of ARSPI-Net, studied on its own.

## Component map

| Concept | Manuscript | Authoritative code | Other copies | Evidence | Tests |
|---|---|---|---|---|---|
| Analysed signal `X_ds`: 256 samples at 256 Hz, 34 channels, spanning -200 to +800 ms, onset at sample 51, z-scored per channel within epoch | Sec. IV-A (`sec:data`) | produced upstream; not in this repository | none | [H] A18, memory #33 | none |
| LIF update: leak `(1-beta)`, multiplicative reset, threshold subtraction, floor at zero; N=256, beta=0.05, theta=0.5 | Sec. III-B, Eqs. 2 and 3 | `analysis/core.py`: `lif_step` | own loops in `regen_reservoir_embedding.regen` and `experiment2_rawsignal.bsc6_all` (different addition order, kept as written) | [H] A1, A2 | `tests/test_reservoir.py` |
| Weights: Xavier-uniform, `RandomState(42)`, input then recurrent draw, rescaled to spectral radius rho (0.9 at the operating point) | Sec. III-B | `core.init_weights` | none | [H] A1. Single weight draw, memory #42 | `tests/test_reservoir.py` |
| BSC6: spike counts over samples [10, 70) in 6 bins of 10; 1536 values per electrode, ordered neuron*6 + bin | Sec. III-B, Eq. `eq:operator` | `core.reservoir_bsc6` | as above | [H] A1. Window is about -160 to +73 ms relative to onset, A18 | `tests/test_reservoir.py` |
| PCA-64 per electrode block, basis shared across electrodes, fit on training subjects of each fold; embedding in R^2176 | Sec. III-B | `experiment_camera_ready.fold_embeddings` | inline in E4 and E5 | [H] A9 | `tests/test_protocol_and_bootstrap.py` |
| Pooled (transductive) PCA sensitivity check | Sec. V-A | `regen_reservoir_embedding.py` then `reanalysis_subject_bootstrap.py` | none | [H] 0.485 [0.447, 0.521] pooled against 0.487 [0.447, 0.523] train-only (`CLAUDE.md`). Required wording is in `CLAUDE.md` | `tests/test_baseline_integrity.py` (values), `tests/test_reservoir.py` (pooled embedding) |
| Baseline A0: band power, Welch, nperseg 256, bands 1-4/4-8/8-13/13-30/30-45 Hz, trapezoid; 170 features | Sec. III-C | `experiment2_rawsignal.bandpower_all` | none on SHAPE (DEAP uses a different, log-mean estimator) | [H] A3: the pickle's `conv_feats` is not used | `tests/test_features_and_fills.py` |
| Baseline A0e: ERP-window means, sample-index windows 80-200, 250-450, 450-800 ms; 102 features | Sec. III-C | `core.erp_window_means` | none | [H] A18 for the onset-relative labels | `tests/test_features_and_fills.py` |
| EEGNet-8,2 comparison, with and without train-time augmentation | Sec. V-C | `experiment_eegnet_signal.py` | none | [H] deterministic rerun, audit section 3 | none |
| Validation protocol: `StratifiedGroupKFold(5, shuffle)`, seeds 42 to 46, subject groups, train-only `StandardScaler`, balanced L2 logistic readout | Sec. IV-B (`sec:validation`) | `core.fit_readout`, constants in `core`; the split loops are in each experiment | split loops in several scripts | [V] identical settings in every script, by reading | `tests/test_protocol_and_bootstrap.py` |
| Out-of-fold aggregation: class probabilities summed over the five partitions, then argmax | Sec. IV-B | each experiment's accumulation loop | several | [V] by reading | `tests/test_protocol_and_bootstrap.py` |
| Subject-level bootstrap: 211 subjects resampled with replacement, three observations kept together, 4000 resamples, percentile interval | Sec. IV-B | `reanalysis_subject_bootstrap.subject_bootstrap`, `paired_diff_ci` | `experiment2_rawsignal.subj_boot` (different seed, superseded output only) | [H] intervals are conditional on masks, models, and the single weight draw, memory #42 | `tests/test_protocol_and_bootstrap.py` |
| Metrics: balanced accuracy, macro-F1, macro one-vs-rest AUC from pooled out-of-fold probabilities | Table I (`tab:clean`) | `experiment_controls.py`, section 5 | none | [H] A7 | `tests/test_manuscript_tables.py`; table manifest (Table I) |
| Signal-level perturbations: electrode removal, 5 dB additive noise, plus or minus 50 ms jitter, shared draws | Sec. III-D, Table III (`tab:rawsignal`) | `analysis/perturbations.py` | none | [H] A8; E2 and E4 agree to 4 decimals for the two fixed baselines, memory #29 | `tests/test_perturbations.py`, `tests/test_manuscript_tables.py`, `tests/test_baseline_integrity.py` (cross-script identities) |
| Feature-coordinate fills: zero, train-mean, kNN (k=10), spatial | Sec. V-B, Table II (`tab:dropconf`), Fig. 3 | `reanalysis_subject_bootstrap.fill_test`, driven by `experiment_camera_ready.run_e2` | none | [H] A14, A15, memory #28 | `tests/test_features_and_fills.py`, `tests/test_manuscript_tables.py` (all Table II cells, including retention). The harness manifest gate still fails on layout, see `docs/HARNESS_OVERRIDES.md` |
| Proposition 1 (zero-fill is not invariant to re-centering) and centeredness `|mu|/sigma` | Sec. III-E, Eq. `eq:noninv` | `experiment_controls.py`, section 4 | none | [H] A11, memory #28, #37 | none |
| Proposition 2 (chance floor of raw retention) | Sec. III-E | derived quantities in Table II; no script computes the retention columns | none | [H] memory #37 | `tests/test_manuscript_tables.py` recomputes both retention columns |
| Spectral-radius sweep and rho = 0 ablation | Sec. V-A, Fig. 1(c) | `experiment_camera_ready.run_e1` | none | [H] memory #35 | none |
| Damage-spreading order parameter, rho* about 0.82 by interpolation | Sec. V-A, Fig. 1(d) | `experiment_camera_ready.damage` | none | [H] A19; reading as a rate-associated crossover, memory #38, #42 | `tests/test_reservoir.py` (pinned values on synthetic drives) |
| Permutation null, PCA component count, BSC1 against BSC6 | Sec. V-A | `experiment_controls.py`, sections 1 to 3 | none | [H] A12; reported as no detected difference, memory #42 | none |
| External check on DEAP: within-subject band power, fill rules | Sec. V-D (`sec:deap`), Fig. 4(a) | `deap_replication.py` | none | [H] audit section 3 | none |

Rows that still say "none" have no automated test: the analysed-signal
preprocessing (upstream), EEGNet (needs torch, not installed in the test
environment), the proposition 1 centeredness computation, the sweep and
control drivers, and DEAP. Their `main()` functions need restricted data.

## Open questions carried from the camera-ready

These are extension work. They are not defects to patch in the baseline.

- [O] Corrected-window rerun: the BSC6 window and ERP windows were specified in
  samples from epoch start, so the reservoir window is mostly pre-stimulus
  (A18, memory #33).
- [O] Pre-threshold membrane histogram to decide the branching reading of rho*
  (memory #38).
- [O] All results rest on one reservoir weight draw (seed 42). No
  multi-draw run exists.
- [O] `conv_feats` in the pickle cannot be reproduced from `X_ds`; its upstream
  preprocessing is unknown (A3).

## Out of scope for this repository

Full ARSPI-Net, E/D/T/C operational distinctness, tPLV graph topology,
structure-function coupling, closed-loop control, clinical or diagnostic
claims, and hardware energy or latency. See `CLAUDE.md`.
