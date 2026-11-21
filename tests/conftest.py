"""Shared fixtures for the project test suite.

The tests run on synthetic signals only. They never read restricted data and
never write into outputs/aggregate/. They observe the accepted implementation
in analysis/ without modifying it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
if str(ANALYSIS) not in sys.path:
    sys.path.insert(0, str(ANALYSIS))


def make_synthetic(n_subjects: int = 12, seed: int = 0):
    """Synthetic stand-in for the analysed signal.

    Shape and conventions follow the real input: (N, 256 samples, 34 channels),
    three condition observations per subject, z-scored per channel within each
    epoch. The content is Gaussian noise plus a class-dependent sinusoid; it has
    no relation to EEG and supports no scientific conclusion.
    """
    rng = np.random.default_rng(seed)
    n = n_subjects * 3
    t = np.arange(256) / 256.0
    y = np.tile(np.arange(3), n_subjects)
    g = np.repeat(np.arange(n_subjects), 3)
    X = rng.standard_normal((n, 256, 34))
    for c in range(3):
        X[y == c] += (0.6 * c) * np.sin(2 * np.pi * (3 + c) * t)[None, :, None]
    X = (X - X.mean(axis=1, keepdims=True)) / X.std(axis=1, keepdims=True)
    return X, y, g


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def synth():
    return make_synthetic()


@pytest.fixture(scope="session")
def aggregate(root):
    import json

    def load(name: str):
        with open(root / "outputs" / "aggregate" / name, encoding="utf-8") as fh:
            return json.load(fh)

    return load


@pytest.fixture(scope="session")
def manuscript_tex(root) -> str:
    return (root / "manuscript" / "main_bibm2026.tex").read_text(encoding="utf-8")
