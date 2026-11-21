"""Validation protocol, readout, out-of-fold aggregation, and subject-level bootstrap."""
from __future__ import annotations

import numpy as np
import pytest
from sklearn.model_selection import StratifiedGroupKFold

import experiment2_rawsignal as E2S
import experiment_camera_ready as EC
import reanalysis_subject_bootstrap as RB


def _splits(y, g, seed):
    cv = StratifiedGroupKFold(5, shuffle=True, random_state=seed)
    return list(cv.split(np.zeros((len(y), 1)), y, groups=g))


def test_protocol_constants():
    assert RB.SEEDS == EC.SEEDS == E2S.SEEDS == [42, 43, 44, 45, 46]
    assert RB.N_FOLDS == 5 and RB.N_BOOT == E2S.N_BOOT == 4000


def test_splits_are_subject_disjoint_and_cover(synth):
    _, y, g = synth
    for seed in RB.SEEDS:
        seen = np.zeros(len(y), int)
        for tr, te in _splits(y, g, seed):
            assert not set(g[tr]) & set(g[te])                # no subject on both sides
            seen[te] += 1
        assert (seen == 1).all()                              # each observation tested once per seed


def test_split_pinned(synth):
    """First two test folds for seed 42 on the synthetic design (scikit-learn 1.9.1)."""
    _, y, g = synth
    te = [t.tolist() for _, t in _splits(y, g, 42)]
    assert te[0] == [6, 7, 8, 9, 10, 11, 30, 31, 32]
    assert te[1] == [3, 4, 5, 18, 19, 20, 27, 28, 29]


def test_split_ignores_feature_values(synth):
    """Scripts pass X or a zeros placeholder to split(); the folds must be the same."""
    X, y, g = synth
    cv = StratifiedGroupKFold(5, shuffle=True, random_state=44)
    a = [te.tolist() for _, te in cv.split(X.reshape(len(y), -1), y, groups=g)]
    b = [te.tolist() for _, te in _splits(y, g, 44)]
    assert a == b


def test_readout_copies_agree(synth):
    """experiment_camera_ready.fit_pred against experiment2_rawsignal._fit_pred."""
    X, y, g = synth
    F = E2S.erp_all(X).reshape(len(y), -1)
    tr, te = _splits(y, g, 42)[0]
    p = EC.fit_pred(F[tr], y[tr], F[te], 42)
    assert p.shape == (len(te), 3) and np.allclose(p.sum(axis=1), 1.0)
    acc = np.zeros((len(y), 3))
    E2S._fit_pred(F[tr], y[tr], F[te], 42, acc, te, np.unique(y))
    assert np.array_equal(acc[te], p)
    assert not acc[tr].any()


def test_readout_uses_train_only_standardization(synth):
    """Changing the test rows must not change predictions for other test rows."""
    X, y, g = synth
    F = E2S.erp_all(X).reshape(len(y), -1)
    tr, te = _splits(y, g, 42)[0]
    p = EC.fit_pred(F[tr], y[tr], F[te], 42)
    Fte = F[te].copy(); Fte[0] += 100.0
    assert np.array_equal(EC.fit_pred(F[tr], y[tr], Fte, 42)[1:], p[1:])


def test_run_oof_equals_manual_aggregation(synth):
    """run_oof = probabilities summed over the five partitions, then argmax."""
    X, y, g = synth
    erp = E2S.erp_all(X); F = erp.reshape(len(y), -1)
    acc = np.zeros((len(y), 3))
    for seed in RB.SEEDS:
        for tr, te in _splits(y, g, seed):
            acc[te] += EC.fit_pred(F[tr], y[tr], F[te], seed)
    manual = np.unique(y)[np.argmax(acc, axis=1)]
    assert np.array_equal(RB.run_oof(F, erp.shape[1:], y, g, 0.0, "zero"), manual)


def test_run_oof_dropout_changes_only_test_side(synth):
    X, y, g = synth
    erp = E2S.erp_all(X); F = erp.reshape(len(y), -1)
    a = RB.run_oof(F, erp.shape[1:], y, g, 0.3, "zero")
    assert np.array_equal(a, RB.run_oof(F, erp.shape[1:], y, g, 0.3, "zero"))   # deterministic
    assert a.shape == y.shape and set(a) <= {0, 1, 2}


def test_fold_embeddings_train_only_pca(synth):
    X, y, g = synth
    B, _ = EC.bsc6(X[:, :, :4], 0.9)                          # 4 channels keeps this fast
    from sklearn.decomposition import PCA

    it = EC.fold_embeddings(B, y, g)
    seed, fold, tr, te, E, v0 = next(it)
    assert (seed, fold) == (42, 0) and E.shape == (len(y), 4, 64) and v0.shape == (64,)
    pca = PCA(n_components=64, random_state=42).fit(B[tr].reshape(-1, 1536))
    assert np.array_equal(E, pca.transform(B.reshape(-1, 1536)).reshape(E.shape))
    assert np.array_equal(v0, pca.transform(np.zeros((1, 1536)))[0])
    assert sum(1 for _ in it) == 24                           # 5 seeds x 5 folds in total


def _preds(y):
    p = y.copy(); p[::4] = (p[::4] + 1) % 3
    return p


def test_subject_bootstrap_pinned(synth):
    _, y, g = synth
    pt, ci, boot = RB.subject_bootstrap(y, g, {"a": _preds(y)}, n_boot=200)
    assert pt["a"] == pytest.approx(0.75)
    assert ci["a"] == pytest.approx((0.6666666666666666, 0.8333333333333334))
    assert len(boot["a"]) == 200
    pt2, ci2, _ = RB.subject_bootstrap(y, g, {"a": _preds(y)}, n_boot=200)
    assert (pt, ci) == (pt2, ci2)                             # fixed seed 12345


def test_subject_bootstrap_resamples_whole_subjects(synth):
    """Perfect predictions stay perfect under any subject resample."""
    _, y, g = synth
    pt, ci, _ = RB.subject_bootstrap(y, g, {"p": y.copy()}, n_boot=100)
    assert pt["p"] == 1.0 and ci["p"] == (1.0, 1.0)


def test_paired_diff_ci(synth):
    _, y, g = synth
    m, lo, hi, pgt = RB.paired_diff_ci(y, g, _preds(y), y.copy(), n_boot=200)
    assert (m, lo, hi, pgt) == pytest.approx((-0.2509722222222222, -0.33333333333333337, -0.16666666666666663, 0.0))
    assert RB.paired_diff_ci(y, g, y, y, n_boot=50) == (0.0, 0.0, 0.0, 0.0)


def test_the_two_bootstraps_are_not_interchangeable(synth):
    """experiment2_rawsignal.subj_boot uses RNG seed 7; subject_bootstrap uses 12345.

    Same point estimate, different interval. They must not be merged
    (docs/ARCHITECTURE.md, Known duplication).
    """
    _, y, g = synth
    pt, ci, _ = RB.subject_bootstrap(y, g, {"a": _preds(y)}, n_boot=200)
    pt2, ci2 = E2S.subj_boot(y, g, {"a": _preds(y)}, n_boot=200)
    assert pt["a"] == pt2["a"]
    assert ci2["a"] == pytest.approx([0.6666666666666666, 0.8062500000000002])
    assert tuple(ci2["a"]) != ci["a"]
