#!/usr/bin/env python3
"""Shared scientific components of the accepted BIBM 2026 analysis.

One definition of the protocol constants, the reservoir weight draw, the LIF
update, the BSC6 code, the ERP-window encoder, and the readout. The experiment
scripts import these instead of carrying their own copies.

This module was extracted from the accepted implementation without changing
any arithmetic. tests/test_refactor_equivalence.py runs the baseline commit and
this code on the same synthetic input and requires bitwise-equal outputs.

Deliberately NOT here (see docs/ARCHITECTURE.md, Known duplication):
  * the reservoir loops in experiment2_rawsignal.bsc6_all and
    regen_reservoir_embedding.regen. They add the input and recurrent currents
    before the leak term, i.e. leak + (input + recurrent), while `lif_step`
    below computes (leak + input) + recurrent. Floating-point addition is not
    associative, so the two forms are kept as they were written. Their spike
    counts are bitwise equal on the synthetic fixture; that has not been shown
    on the restricted data.
  * the two subject bootstraps, which use different RNG seeds.
  * the PCA step. Scripts differ on purpose between fit_transform (pooled
    sensitivity check) and fit followed by transform (train-only main results).
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# --- reservoir -------------------------------------------------------------
N_RES, BETA, THETA, SEED = 256, 0.05, 0.5, 42
# BSC6: spike counts over samples [T_START, T_END) in BSC_N_BINS equal bins;
# PCA_K components per electrode block.
BSC_N_BINS, T_START, T_END, PCA_K = 6, 10, 70, 64

# --- validation protocol ---------------------------------------------------
SEEDS = [42, 43, 44, 45, 46]
N_FOLDS = 5
N_BOOT = 4000

# --- analysed signal and baseline encoders ---------------------------------
FS = 256  # Hz
# Windows are in sample-index milliseconds (sample / 256 Hz), measured from the FIRST sample of
# X_ds, which is 200 ms before stimulus onset (X_ds == raw[0:1024:4]; onset at raw sample 205,
# X_ds sample 51). Relative to onset they span about -120..0, 50..250 and 250..600 ms.
ERP_WINDOWS_MS = [(80, 200), (250, 450), (450, 800)]
BANDS = [(1, 4), (4, 8), (8, 13), (13, 30), (30, 45)]


def init_weights(rho: float = 0.9):
    """Source initialization (Xavier-uniform, seed 42); W rescaled to spectral radius rho.

    The input weights are drawn first and do not depend on rho. rho = 0 gives a
    zero recurrent matrix (a feedforward LIF layer).
    """
    rng = np.random.RandomState(SEED)
    lin = np.sqrt(6.0 / (1 + N_RES)); W_in = rng.uniform(-lin, lin, (N_RES, 1))
    lrec = np.sqrt(6.0 / (2 * N_RES)); W = rng.uniform(-lrec, lrec, (N_RES, N_RES))
    W *= rho / np.abs(np.linalg.eigvals(W)).max()
    return W_in, W


def lif_step(mem, spk, drive, W):
    """One LIF update for a batch of drives: returns (membrane, spikes).

    Leak (1 - BETA) with multiplicative reset by the previous spike, input and
    recurrent currents, threshold THETA, threshold subtraction, floor at zero.
    The order of the three additions is part of the accepted implementation.
    """
    mem = (1.0 - BETA) * mem * (1.0 - spk) + drive + W @ spk
    spk = (mem >= THETA).astype(np.float64)
    mem = np.maximum(mem - spk * THETA, 0.0)
    return mem, spk


def reservoir_bsc6(X_ds, rho: float):
    """BSC6 for every (obs, channel) drive: returns (N, n_ch, N_RES * 6) and mean firing rate.

    Each electrode trace drives the same reservoir independently. Column order
    within an electrode block is neuron * BSC_N_BINS + bin.
    """
    N, T, n_ch = X_ds.shape; C = N * n_ch
    S = np.transpose(X_ds, (1, 0, 2)).reshape(T, C)
    W_in, W = init_weights(rho); win0 = W_in[:, 0][:, None]
    mem = np.zeros((N_RES, C)); spk = np.zeros((N_RES, C))
    counts = np.zeros((N_RES, BSC_N_BINS, C), dtype=np.float32)
    binw = (T_END - T_START) // BSC_N_BINS
    for t in range(T):
        mem, spk = lif_step(mem, spk, win0 * S[t][None, :], W)
        if T_START <= t < T_END:
            counts[:, (t - T_START) // binw, :] += spk
    rate = float(counts.sum() / (N_RES * C * (T_END - T_START)))
    return counts.reshape(N_RES * BSC_N_BINS, C).T.reshape(N, n_ch, -1), rate


def erp_window_means(X_ds):
    """ERP-window encoder: mean amplitude in each ERP_WINDOWS_MS window, per channel."""
    N, T, n_ch = X_ds.shape
    out = np.zeros((N, n_ch, len(ERP_WINDOWS_MS)))
    for w, (a, b) in enumerate(ERP_WINDOWS_MS):
        out[:, :, w] = X_ds[:, int(round(a / 1000 * FS)):int(round(b / 1000 * FS)), :].mean(axis=1)
    return out


def fit_readout(Xtr, ytr, seed: int):
    """Train-only StandardScaler and the balanced L2 logistic readout. Returns (scaler, model)."""
    sc = StandardScaler().fit(Xtr)
    clf = LogisticRegression(max_iter=2000, C=1.0, class_weight="balanced",
                             solver="lbfgs", random_state=seed).fit(sc.transform(Xtr), ytr)
    return sc, clf


def readout_proba(Xtr, ytr, Xte, seed: int):
    """Class probabilities for Xte from a readout fitted on (Xtr, ytr)."""
    sc, clf = fit_readout(Xtr, ytr, seed)
    return clf.predict_proba(sc.transform(Xte))
