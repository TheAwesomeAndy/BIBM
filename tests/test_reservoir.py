"""Characterization of the LIF reservoir and the BSC6 code on synthetic drives.

These tests pin the behavior of the accepted implementation. They do not assert
that the behavior is scientifically right; they assert that it does not change.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest

import experiment2_rawsignal as E2S
import experiment_camera_ready as EC
import regen_reservoir_embedding as RG


@pytest.fixture(scope="module")
def bsc(synth):
    X, _, _ = synth
    return EC.bsc6(X, 0.9)


@pytest.fixture(scope="module")
def golden(root):
    return json.loads((root / "tests" / "golden" / "synthetic_reservoir.json").read_text())


def test_constants_agree_across_copies():
    for m in (E2S, RG):
        assert (m.N_RES, m.BETA, m.THETA, m.SEED) == (EC.N_RES, EC.BETA, EC.THETA, EC.SEED)
        assert (m.BSC_N_BINS, m.T_START, m.T_END, m.PCA_K) == (EC.BSC_N_BINS, EC.T_START, EC.T_END, EC.PCA_K)
        assert m.SEEDS == EC.SEEDS
    assert (EC.N_RES, EC.BETA, EC.THETA, EC.SEED) == (256, 0.05, 0.5, 42)
    assert (EC.BSC_N_BINS, EC.T_START, EC.T_END, EC.PCA_K) == (6, 10, 70, 64)
    assert EC.SEEDS == [42, 43, 44, 45, 46]


def test_weight_initializers_are_identical():
    w_in, w = EC.weights(0.9)
    for init in (E2S.init_weights, RG.init_weights):
        w_in2, w2 = init()
        assert np.array_equal(w_in, w_in2)
        assert np.array_equal(w, w2)


def test_weights_shape_and_spectral_radius():
    w_in, w = EC.weights(0.9)
    assert w_in.shape == (256, 1) and w.shape == (256, 256)
    assert np.abs(np.linalg.eigvals(w)).max() == pytest.approx(0.9, abs=1e-12)
    for rho in (0.3, 1.5):
        assert np.abs(np.linalg.eigvals(EC.weights(rho)[1])).max() == pytest.approx(rho, abs=1e-12)
    assert not EC.weights(0.0)[1].any()                      # rho = 0 removes the recurrence
    assert np.array_equal(EC.weights(0.0)[0], w_in)          # input weights do not depend on rho


def test_bsc6_shape_dtype_and_range(synth, bsc):
    X, _, _ = synth
    B, rate = bsc
    assert B.shape == (X.shape[0], 34, 1536) and B.dtype == np.float32
    assert B.min() >= 0 and B.max() <= 10                    # at most one spike per step, 10 steps per bin
    assert np.array_equal(B, np.round(B))                    # spike counts are integers
    assert rate == pytest.approx(B.sum() / (256 * X.shape[0] * 34 * 60))


def test_bsc6_implementations_are_bitwise_equal(synth, bsc):
    """experiment_camera_ready.bsc6 at rho 0.9 against experiment2_rawsignal.bsc6_all."""
    X, _, _ = synth
    assert np.array_equal(bsc[0], E2S.bsc6_all(X))


def test_regen_embedding_equals_pooled_pca_of_bsc6(synth, bsc):
    """regen() is the same reservoir followed by one pooled PCA.fit_transform."""
    from sklearn.decomposition import PCA

    X, _, _ = synth
    emb, _ = RG.regen(X)
    ref = PCA(n_components=64, random_state=42).fit_transform(bsc[0].reshape(-1, 1536))
    assert emb.shape == (X.shape[0], 34, 64)
    assert np.array_equal(emb, ref.reshape(emb.shape))


def test_bsc6_layout_is_neuron_major(synth, bsc):
    """Column order is neuron*6 + bin (experiment_controls builds BSC1 from this)."""
    X, _, _ = synth
    w_in, w = EC.weights(0.9)
    s = X[0, :, 0]
    mem = np.zeros(256); spk = np.zeros(256); counts = np.zeros((256, 6))
    for t in range(256):
        mem = (1.0 - EC.BETA) * mem * (1.0 - spk) + w_in[:, 0] * s[t] + w @ spk
        spk = (mem >= EC.THETA).astype(float)
        mem = np.maximum(mem - spk * EC.THETA, 0.0)
        if 10 <= t < 70:
            counts[:, (t - 10) // 10] += spk
    assert np.array_equal(bsc[0][0, 0], counts.reshape(-1).astype(np.float32))


def test_bsc6_is_per_drive(synth, bsc):
    """Each (observation, channel) trace is encoded independently of the others."""
    X, _, _ = synth
    sub, _ = EC.bsc6(X[3:5], 0.9)
    assert np.array_equal(sub, bsc[0][3:5])


def test_zero_drive_gives_zero_code():
    """A removed electrode (zero trace) yields no spikes (relied on by E4)."""
    B, rate = EC.bsc6(np.zeros((2, 256, 34)), 0.9)
    assert not B.any() and rate == 0.0


def test_bsc6_deterministic(synth, bsc):
    X, _, _ = synth
    again, rate = EC.bsc6(X, 0.9)
    assert np.array_equal(again, bsc[0]) and rate == bsc[1]


def test_bsc6_matches_golden(bsc, golden):
    """Pinned values from the baseline implementation (numpy 2.4.6).

    Exact spike counts depend on floating-point matrix products, so a different
    BLAS build could in principle flip a threshold comparison. If this test
    fails while test_bsc6_implementations_are_bitwise_equal passes, suspect the
    environment before the code.
    """
    B, rate = bsc
    g = golden["rho_0.9"]
    assert float(B.sum()) == g["total_spikes"]
    assert B.reshape(-1, 256, 6).sum(axis=(0, 1)).tolist() == g["spikes_per_bin"]
    assert rate == pytest.approx(g["firing_rate"], rel=1e-12)
    assert hashlib.sha256(np.ascontiguousarray(B).tobytes()).hexdigest() == g["sha256"]


def test_rho_zero_matches_golden(synth, golden):
    X, _, _ = synth
    B, _ = EC.bsc6(X[:3], 0.0)
    assert float(B.sum()) == golden["rho_0.0_first3"]["total_spikes"]


def test_damage_statistic(synth, golden):
    X, _, _ = synth
    d = EC.damage(X, 0.9, n_drive=50)
    assert d == EC.damage(X, 0.9, n_drive=50)                # fixed RNG seed
    assert d == pytest.approx(golden["damage_n50"]["rho_0.9"], rel=1e-12)
    assert EC.damage(X, 0.0, n_drive=50) == pytest.approx(golden["damage_n50"]["rho_0.0"], rel=1e-12)
    assert 0.0 <= d <= 1.0
