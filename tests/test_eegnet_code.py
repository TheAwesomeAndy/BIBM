"""Characterization of analysis/experiment_eegnet_signal.py (E3) on synthetic data.

Needs torch (optional extra `eegnet` in pyproject.toml); the whole module is
skipped without it. Training is exercised for two epochs on a small synthetic
set to pin determinism, not accuracy. main() is not called: it needs the
restricted data and writes into outputs/aggregate/.
"""
from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

import experiment_eegnet_signal as E3  # noqa: E402
import perturbations as PT  # noqa: E402


def test_constants_pinned():
    assert E3.SEEDS == [42, 43, 44, 45, 46]
    assert E3.LEVELS == [0.0, 0.1, 0.3, 0.5]
    assert (E3.EPOCHS, E3.BATCH, E3.LR, E3.DROPOUT) == (80, 64, 1e-3, 0.25)
    assert torch.get_num_threads() == 2                          # set at import; determinism was observed with it


def test_architecture():
    """EEGNet-8,2: F1=8, D=2, F2=16, temporal kernel 64, for 34 channels x 256 samples."""
    torch.manual_seed(0)
    net = E3.EEGNet()
    assert net.fc.in_features == 128 and net.fc.out_features == 3
    # temporal conv 8*64 = 512; depthwise spatial 16*34 = 544; separable 16*16 + 16*16 = 512;
    # batch norms 2*(8 + 16 + 16) = 80; classifier 128*3 + 3 = 387
    assert sum(p.numel() for p in net.parameters()) == 512 + 544 + 512 + 80 + 387 == 2035
    convs = [m for m in net.net if isinstance(m, torch.nn.Conv2d)]
    assert [tuple(c.kernel_size) for c in convs] == [(1, 64), (34, 1), (1, 16), (1, 1)]
    assert [c.out_channels for c in convs] == [8, 16, 16, 16]
    assert all(c.bias is None for c in convs)
    net.eval()
    with torch.no_grad():
        out = net(torch.zeros(5, 1, 34, 256))
    assert out.shape == (5, 3)


def test_to_input_layout_and_standardization(synth):
    X, _, _ = synth
    mu = X.mean(axis=(0, 1)); sd = X.std(axis=(0, 1)) + 1e-8
    xin = E3.to_input(X, mu, sd)
    assert xin.shape == (X.shape[0], 1, 34, 256)                 # (n, 1, channels, time)
    assert np.array_equal(xin[3, 0, 7, :], (X[3, :, 7] - mu[7]) / sd[7])


def test_conditions_use_shared_draws(synth):
    X, _, _ = synth
    got = dict(E3.conditions(X[:6], 43, 2))
    assert list(got) == ["remove_0.0", "remove_0.1", "remove_0.3", "remove_0.5", "amp_5dB", "jitter_50ms"]
    assert np.array_equal(got["remove_0.0"], X[:6])
    assert np.array_equal(got["remove_0.3"], PT.remove_channels(X[:6], 0.3, 43, 2)[0])
    assert np.array_equal(got["amp_5dB"], PT.amplitude_noise(X[:6], 5.0, 43, 2))
    assert np.array_equal(got["jitter_50ms"], PT.temporal_jitter(X[:6], 50.0, 43, 2))


def test_augment_semantics():
    gen = torch.Generator().manual_seed(1)
    x = torch.ones(400, 1, 34, 256)
    a = E3.augment(x, gen)
    assert a.shape == x.shape
    assert torch.equal(a, E3.augment(x, torch.Generator().manual_seed(1)))   # deterministic given the generator
    # a zeroed channel leaves only the additive noise, so its mean is far from 1
    dropped = (a.mean(dim=3).squeeze(1) - 1.0).abs() > 0.5
    per_sample = dropped.sum(dim=1)
    assert int(per_sample.max()) <= 17                           # at most half of 34 channels
    untouched = float((per_sample == 0).float().mean())
    assert 0.40 < untouched < 0.65                               # about half the samples keep every channel
    noise_sd = (a - a.mean(dim=3, keepdim=True)).std(dim=3).mean(dim=(1, 2))
    assert float(noise_sd.max()) <= 0.55 and float(noise_sd.min()) >= 0.0    # std ~ U(0, 0.5)


def test_training_is_deterministic(synth, monkeypatch):
    X, y, _ = synth
    mu = X.mean(axis=(0, 1)); sd = X.std(axis=(0, 1)) + 1e-8
    xin = E3.to_input(X, mu, sd)
    monkeypatch.setattr(E3, "EPOCHS", 2)

    def weights(seed, aug):
        net = E3.train_eegnet(xin, y, seed, aug)
        assert not net.training                                  # returned in eval mode
        return torch.cat([p.detach().flatten() for p in net.parameters()])

    a = weights(4200, False)
    assert torch.equal(a, weights(4200, False))                  # same seed, same weights
    assert not torch.equal(a, weights(4201, False))              # seed matters
    b = weights(4200, True)
    assert torch.equal(b, weights(4200, True))
    assert not torch.equal(a, b)                                 # augmentation changes training
