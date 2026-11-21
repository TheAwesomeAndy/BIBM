"""Baseline encoders (band power, ERP-window) and the four fill rules."""
from __future__ import annotations

import numpy as np
import pytest
from scipy.signal import welch

import experiment2_rawsignal as E2S
import reanalysis_subject_bootstrap as RB


def test_windows_and_bands_pinned():
    assert E2S.ERP_WINDOWS_MS == RB.ERP_WINDOWS_MS == [(80, 200), (250, 450), (450, 800)]
    assert E2S.BANDS == [(1, 4), (4, 8), (8, 13), (13, 30), (30, 45)]
    assert E2S.FS == RB.FS == 256


def test_erp_window_values(synth):
    X, _, _ = synth
    erp = E2S.erp_all(X)
    assert erp.shape == (X.shape[0], 34, 3)
    # sample-index windows, measured from the first sample of the epoch (CODE_AUDIT A18)
    for w, (a, b) in enumerate([(20, 51), (64, 115), (115, 205)]):
        assert np.allclose(erp[:, :, w], X[:, a:b, :].mean(axis=1), rtol=0, atol=0)


def test_erp_window_copies_agree(synth):
    """erp_all against the block built in reanalysis_subject_bootstrap.build_blocks."""
    X, y, _ = synth
    d = {"y": y, "X_ds": X, "conv_feats": np.ones((len(y), 34, 5)), "lsm_bsc6_pca": np.ones((len(y), 34, 64))}
    d["lsm_bsc6_pca"][0, 0, 0] = 2.0                          # non-constant, so no .npy fallback is read
    blocks = RB.build_blocks(d)
    assert np.array_equal(blocks["ERP-window"][0], E2S.erp_all(X).reshape(len(y), -1))
    assert blocks["ERP-window"][1] == (34, 3)
    assert blocks["Band-power"][1] == (34, 5) and blocks["Reservoir"][1] == (34, 64)


def test_bandpower_definition(synth):
    X, _, _ = synth
    bp = E2S.bandpower_all(X[:2])
    assert bp.shape == (2, 34, 5) and (bp > 0).all()
    f, p = welch(X[1, :, 7], fs=256, nperseg=256)
    for bi, (lo, hi) in enumerate(E2S.BANDS):
        m = (f >= lo) & (f <= hi)
        assert bp[1, 7, bi] == pytest.approx(np.trapezoid(p[m], f[m]), rel=1e-12)


def test_silent_channel_features_are_zero():
    """Memory entry #29: a flat trace has zero band power and zero window means."""
    z = np.zeros((1, 256, 34))
    assert not E2S.bandpower_all(z).any() and not E2S.erp_all(z).any()


@pytest.fixture()
def blocks():
    rng = np.random.default_rng(3)
    n_ch, n_feat = 6, 4
    Xtr = rng.standard_normal((40, n_ch * n_feat)) + 2.0
    Xte = rng.standard_normal((9, n_ch * n_feat)) + 2.0
    drop, keep, _ = RB.drop_channels((n_ch, n_feat), 0.34, np.random.default_rng(0))
    return Xtr, Xte, (n_ch, n_feat), drop, keep


def test_fills_pinned_list():
    assert RB.FILLS == ["zero", "mean", "knn", "spatial"]
    assert RB.DROP_LEVELS == [0.1, 0.2, 0.3, 0.4, 0.5]


@pytest.mark.parametrize("fill", ["zero", "mean", "knn", "spatial"])
def test_fill_touches_only_dropped_columns(blocks, fill):
    Xtr, Xte, shape, drop, keep = blocks
    before = Xte.copy()
    out = RB.fill_test(Xte, Xtr, shape, drop, keep, fill)
    assert np.array_equal(Xte, before)                        # input not modified
    assert np.allclose(out[:, keep], Xte[:, keep])
    assert drop.size == 2 and (~keep).sum() == 8


def test_fill_values(blocks):
    Xtr, Xte, shape, drop, keep = blocks
    dropped = np.where(~keep)[0]
    assert not RB.fill_test(Xte, Xtr, shape, drop, keep, "zero")[:, dropped].any()
    mean = RB.fill_test(Xte, Xtr, shape, drop, keep, "mean")
    assert np.allclose(mean[:, dropped], np.broadcast_to(Xtr[:, dropped].mean(0), (len(Xte), dropped.size)))
    sp = RB.fill_test(Xte, Xtr, shape, drop, keep, "spatial").reshape(len(Xte), *shape)
    kept_ch = np.setdiff1d(np.arange(shape[0]), drop)
    for c in drop:
        assert np.allclose(sp[:, c, :], Xte.reshape(len(Xte), *shape)[:, kept_ch, :].mean(axis=1))
    knn = RB.fill_test(Xte, Xtr, shape, drop, keep, "knn")
    assert np.isfinite(knn).all()
    assert Xtr[:, dropped].min() <= knn[:, dropped].min() and knn[:, dropped].max() <= Xtr[:, dropped].max()


def test_no_drop_returns_input(blocks):
    Xtr, Xte, shape, _, _ = blocks
    d, keep, _ = RB.drop_channels(shape, 0.0, np.random.default_rng(0))
    assert d.size == 0 and keep.all()
    assert RB.fill_test(Xte, Xtr, shape, d, keep, "zero") is Xte
