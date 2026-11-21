"""Signal-level perturbations (analysis/perturbations.py): shared draws, shapes, semantics."""
from __future__ import annotations

import numpy as np
import pytest

import perturbations as PT
import reanalysis_subject_bootstrap as RB


def test_removal_draw_pinned():
    """The (seed 42, fold 0) draw at 30% of 34 electrodes. Pins the RNG keying."""
    assert PT.removal_draw(34, 0.3, 42, 0).tolist() == [14, 2, 12, 24, 4, 26, 8, 13, 1, 9]


@pytest.mark.parametrize("frac, n", [(0.1, 3), (0.2, 7), (0.3, 10), (0.4, 14), (0.5, 17)])
def test_removal_count(frac, n):
    d = PT.removal_draw(34, frac, 43, 2)
    assert d.size == n and np.unique(d).size == n and d.min() >= 0 and d.max() < 34


def test_removal_draw_matches_every_inline_copy():
    """All experiments must lose the same electrodes in a given (seed, fold)."""
    for seed in (42, 46):
        for fold in (0, 4):
            ref = PT.removal_draw(34, 0.3, seed, fold)
            # reanalysis_subject_bootstrap.run_oof / experiment_camera_ready.run_e2
            d, keep, _ = RB.drop_channels((34, 3), 0.3, np.random.default_rng(1000 * seed + fold))
            assert np.array_equal(d, ref)
            assert keep.reshape(34, 3)[ref].sum() == 0 and keep.sum() == (34 - ref.size) * 3
            # experiment_camera_ready.e1_conditions, experiment2_rawsignal, experiment_controls
            inline = np.random.default_rng(1000 * seed + fold).choice(34, int(round(0.3 * 34)), replace=False)
            assert np.array_equal(inline, ref)


def test_remove_channels(synth):
    X, _, _ = synth
    Xc, drop = PT.remove_channels(X, 0.3, 42, 1)
    keep = np.setdiff1d(np.arange(34), drop)
    assert not Xc[:, :, drop].any()
    assert np.array_equal(Xc[:, :, keep], X[:, :, keep])
    assert Xc is not X and X[:, :, drop].any()               # input not modified
    X0, d0 = PT.remove_channels(X, 0.0, 42, 1)
    assert d0.size == 0 and np.array_equal(X0, X)


def test_amplitude_noise_snr_and_determinism(synth):
    X, _, _ = synth
    a = PT.amplitude_noise(X, 5.0, 42, 0)
    assert np.array_equal(a, PT.amplitude_noise(X, 5.0, 42, 0))
    assert not np.array_equal(a, PT.amplitude_noise(X, 5.0, 42, 1))
    noise = a - X
    snr = 10 * np.log10((X ** 2).mean() / (noise ** 2).mean())
    assert snr == pytest.approx(5.0, abs=0.1)


def test_amplitude_noise_leaves_silent_channel_silent(synth):
    X, _, _ = synth
    Xz = X.copy(); Xz[:, :, 5] = 0.0
    assert not PT.amplitude_noise(Xz, 5.0, 42, 0)[:, :, 5].any()


def test_temporal_jitter(synth):
    X, _, _ = synth
    J = PT.temporal_jitter(X, 50.0, 42, 0)
    assert J.shape == X.shape and np.array_equal(J, PT.temporal_jitter(X, 50.0, 42, 0))
    k = int(round(50.0 / 1000.0 * PT.FS))
    assert k == 13
    shifts = np.random.default_rng(20_000 + 1000 * 42 + 0).integers(-k, k + 1, X.shape[0])
    for i, s in enumerate(shifts):
        if s > 0:                                            # delayed, start padded with the first sample
            assert np.array_equal(J[i, s:], X[i, :-s]) and np.array_equal(J[i, :s], np.repeat(X[i, :1], s, 0))
        elif s < 0:                                          # advanced, end padded with the last sample
            assert np.array_equal(J[i, :s], X[i, -s:]) and np.array_equal(J[i, s:], np.repeat(X[i, -1:], -s, 0))
        else:
            assert np.array_equal(J[i], X[i])
    assert np.array_equal(PT.temporal_jitter(X, 0.0, 42, 0), X)


def test_signal_conditions_registry(synth):
    X, _, _ = synth
    assert list(PT.SIGNAL_CONDITIONS) == ["amp_5dB", "jitter_50ms"]
    assert np.array_equal(PT.SIGNAL_CONDITIONS["amp_5dB"](X, 43, 2), PT.amplitude_noise(X, 5.0, 43, 2))
    assert np.array_equal(PT.SIGNAL_CONDITIONS["jitter_50ms"](X, 43, 2), PT.temporal_jitter(X, 50.0, 43, 2))
