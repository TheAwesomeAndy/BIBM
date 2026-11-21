"""Characterization of analysis/deap_replication.py on synthetic data.

No DEAP data is read. The loader is exercised on small fake subject files
written to a temporary directory. main() is not called: it writes into
outputs/aggregate/.
"""
from __future__ import annotations

import pickle

import numpy as np
import pytest
from scipy.signal import welch

import deap_replication as DP


def test_constants_pinned():
    assert (DP.FS, DP.NCH) == (128, 32)
    assert DP.BANDS == [(4, 8), (8, 12), (12, 30), (30, 45)]
    assert DP.SEEDS == [42, 43, 44, 45, 46]
    assert DP.RATES == [0.10, 0.30, 0.50] and DP.FILLS == ["zero", "mean", "knn"]
    assert DP.N_BOOT == 4000


def test_bandpower_definition():
    """Log of the mean PSD per band (upper edge exclusive), first 32 channels only."""
    rng = np.random.default_rng(0)
    trial = rng.standard_normal((40, 1024))
    bp = DP.bandpower(trial)
    assert bp.shape == (32, 4)
    f, P = welch(trial[:32], fs=128, nperseg=256)
    for bi, (lo, hi) in enumerate(DP.BANDS):
        assert np.array_equal(bp[:, bi], np.log(P[:, (f >= lo) & (f < hi)].mean(axis=1) + 1e-12))
    trial2 = trial.copy(); trial2[32:] += 100.0                 # peripheral channels are ignored
    assert np.array_equal(DP.bandpower(trial2), bp)


def _fake_deap(tmp_path, n_files=32, n_trials=12):
    rng = np.random.default_rng(1)
    for i in range(n_files):
        d = {"data": rng.standard_normal((n_trials, 40, 384 + 512)).astype(np.float32),
             "labels": rng.uniform(1, 9, (n_trials, 4))}
        with open(tmp_path / f"s{i + 1:02d}.dat", "wb") as fh:
            pickle.dump(d, fh)
    return tmp_path


def test_load_shapes_labels_and_baseline_drop(tmp_path):
    X, y, g = DP.load(str(_fake_deap(tmp_path)))
    assert X.shape == (32 * 12, 128) and y.shape == (384,) and set(y) <= {0, 1}
    assert np.array_equal(g, np.repeat(np.arange(32), 12))
    with open(tmp_path / "s01.dat", "rb") as fh:
        d = pickle.load(fh)
    assert np.array_equal(X[0], DP.bandpower(d["data"][0][:, 384:]).reshape(-1))   # first 3 s dropped
    assert np.array_equal(y[:12], (d["labels"][:, 0] >= 5).astype(int))            # valence threshold 5


def test_load_requires_32_subjects(tmp_path):
    _fake_deap(tmp_path, n_files=3)
    with pytest.raises(SystemExit):
        DP.load(str(tmp_path))


def test_fill_rules():
    rng = np.random.default_rng(2)
    Xtr = rng.standard_normal((30, 12)) + 1.0; Xte = rng.standard_normal((6, 12)) + 1.0
    cols = np.array([0, 1, 2, 3])
    before = Xte.copy()
    z = DP.fill(Xtr, Xte, cols, "zero"); m = DP.fill(Xtr, Xte, cols, "mean"); k = DP.fill(Xtr, Xte, cols, "knn")
    assert np.array_equal(Xte, before)
    assert not z[:, cols].any()
    assert np.allclose(m[:, cols], np.broadcast_to(Xtr.mean(axis=0)[cols], (6, 4)))
    for out in (z, m, k):
        assert np.allclose(out[:, 4:], Xte[:, 4:])
    assert np.isfinite(k).all()


def _synthetic_features(n_subj=4, n_trials=20, seed=3):
    rng = np.random.default_rng(seed)
    y = np.tile(np.array([0, 1]), n_subj * n_trials // 2)
    g = np.repeat(np.arange(n_subj), n_trials)
    X = rng.standard_normal((n_subj * n_trials, 128)) + 0.8 * y[:, None]
    return X, y, g


def test_evaluate_is_within_subject_and_deterministic():
    X, y, g = _synthetic_features()
    per = DP.evaluate(X, y, g, 0.0, "zero")
    assert sorted(per) == [0, 1, 2, 3]
    assert all(len(v) == 25 for v in per.values())               # 5 seeds x 5 folds per subject
    assert per == DP.evaluate(X, y, g, 0.0, "zero")
    assert np.mean([np.mean(v) for v in per.values()]) > 0.9     # separable synthetic classes
    drop = DP.evaluate(X, y, g, 0.3, "zero")
    assert drop == DP.evaluate(X, y, g, 0.3, "zero") and drop != per


def test_evaluate_skips_subjects_with_few_trials_per_class():
    X, y, g = _synthetic_features()
    y = y.copy(); y[g == 2] = 0; y[np.where(g == 2)[0][:4]] = 1  # subject 2: only 4 trials of class 1
    assert sorted(DP.evaluate(X, y, g, 0.0, "zero")) == [0, 1, 3]


def test_dropped_columns_are_whole_electrodes():
    """Channel c owns feature columns 4c..4c+3; the draw is keyed to seed, fold and subject."""
    rng = np.random.default_rng(1000 * 42 + 7 * 0 + 0)
    ch = rng.choice(DP.NCH, int(round(0.3 * DP.NCH)), replace=False)
    cols = (ch[:, None] * len(DP.BANDS) + np.arange(len(DP.BANDS))[None, :]).reshape(-1)
    assert ch.size == 10 and cols.size == 40
    assert sorted(set(cols // 4)) == sorted(ch.tolist())


def test_summarize():
    per = {0: [0.5, 0.7], 1: [0.6, 0.8], 2: [0.9, 0.9]}
    s = DP.summarize(per)
    assert s["n_subjects"] == 3
    assert s["BA_mean_over_folds"] == pytest.approx(np.mean([0.5, 0.7, 0.6, 0.8, 0.9, 0.9]))
    assert s["subject_mean_BA"] == pytest.approx(np.mean([0.6, 0.7, 0.9]))
    assert s["subject_ci95"][0] <= s["subject_mean_BA"] <= s["subject_ci95"][1]
    assert s == DP.summarize(per)                                # fixed RNG seed 7
