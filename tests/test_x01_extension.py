"""Extension experiment X01-2026-11 on synthetic stand-in files.

No restricted data is read. Fake raw epochs and a fake feature pickle are written to a
temporary directory in the documented formats. These tests show that the experiment code
does what its design says; they produce no scientific result.
"""
from __future__ import annotations

import importlib.util
import json
import pickle

import numpy as np
import pytest

import core


@pytest.fixture(scope="module")
def x01(root):
    spec = importlib.util.spec_from_file_location("run_x01", root / "experiments" / "X01-2026-11" / "run_x01.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_fake_shape(directory, subject_ids, seed=0, comma=False):
    rng = np.random.default_rng(seed)
    t = np.arange(1229)
    for sid in subject_ids:
        for ci, cond in enumerate(("Neg", "Neu", "Pos")):
            ep = rng.standard_normal((1229, 34)) + (0.8 * ci) * np.sin(2 * np.pi * t / 400.0)[:, None] * (t > 205)[:, None]
            ep -= ep[:205].mean(axis=0, keepdims=True)                       # baseline correction
            np.savetxt(directory / f"SHAPE_Community_{sid}_IAPS{cond}_BC.txt", ep, fmt="%.8f",
                       delimiter="," if comma else " ")


@pytest.fixture(scope="module")
def fake(tmp_path_factory, x01):
    d = tmp_path_factory.mktemp("fake_shape")
    ids = [f"{i:03d}" for i in (3, 11, 20, 45, 101, 127, 130, 131, 140, 150, 151)]   # 127 must be dropped
    _write_fake_shape(d, ids)
    (d / "SHAPE_Community_999_IAPSNeg_BC.txt").write_text((d / "SHAPE_Community_003_IAPSNeg_BC.txt").read_text())
    raw, y, g, info = x01.load_raw(d)                                        # 999 is incomplete
    X = x01.analysed_signal(raw)
    pkl = d / "features.pkl"
    with open(pkl, "wb") as fh:
        pickle.dump({"X_ds": x01.scale(X, "A_epoch_z").astype(np.float32), "y": y,
                     "subjects": np.array([int(s) for s in g])}, fh)
    return d, raw, X, y, g, info, pkl


def test_loader_selection_order_and_labels(fake):
    _, raw, X, y, g, info, _ = fake
    assert info["n_subjects_complete"] == 10 and info["n_observations"] == 30
    assert "127" not in set(g) and "999" not in set(g)
    assert list(dict.fromkeys(g)) == ["003", "011", "020", "045", "101", "130", "131", "140", "150", "151"]
    assert y.tolist() == [0, 1, 2] * 10
    assert raw.shape == (30, 1229, 34) and X.shape == (30, 256, 34)
    assert np.array_equal(X, raw[:, 0:1024:4, :])
    assert len(info["raw_files_sha256_of_sorted_sha256"]) == 64


def test_loader_rejects_wrong_shape(tmp_path, x01):
    for cond in ("Neg", "Neu", "Pos"):
        np.savetxt(tmp_path / f"SHAPE_Community_5_IAPS{cond}_BC.txt", np.zeros((34, 1229)))
    with pytest.raises(SystemExit):
        x01.load_raw(tmp_path)


def test_scalings(fake, x01):
    X = fake[2]
    A, B, C, D = (x01.scale(X, s) for s in x01.SCALINGS)
    assert np.allclose(A.mean(axis=1), 0) and np.allclose(A.std(axis=1), 1)
    assert np.allclose(B[:, :51].std(axis=1), 1) and np.allclose(B * X[:, :51].std(axis=1, keepdims=True), X)
    assert np.array_equal(C, X) and C is not X
    assert np.allclose(D[:, 51:].mean(axis=1), 0) and np.allclose(D[:, 51:].std(axis=1), 1)
    Xz = X.copy(); Xz[0, :, 0] = 0.0
    with pytest.raises(SystemExit):
        x01.scale(Xz, "A_epoch_z")                                           # zero SD stops the run


def test_step0_pass_and_fail(fake, x01, tmp_path):
    _, _, X, y, g, _, pkl = fake
    ok = x01.step0(X, y, g, pkl)
    assert ok["passed"] and ok["subject_order_match"] and ok["labels_match"]
    assert ok["max_abs_difference"] < 1e-6                                   # float32 storage only
    with open(pkl, "rb") as fh:
        d = pickle.load(fh)
    bad = dict(d); bad["subjects"] = d["subjects"][::-1].copy()
    p2 = tmp_path / "reordered.pkl"; pickle.dump(bad, open(p2, "wb"))
    r = x01.step0(X, y, g, p2)
    assert not r["passed"] and not r["subject_order_match"]
    bad = dict(d); bad["X_ds"] = d["X_ds"] * 1.01
    p3 = tmp_path / "scaled.pkl"; pickle.dump(bad, open(p3, "wb"))
    r = x01.step0(X, y, g, p3)
    assert not r["passed"] and r["max_abs_difference"] > x01.STEP0_TOL


def test_r1_is_the_accepted_reservoir(fake, x01):
    """The generic counter with the accepted window equals core.reservoir_bsc6 bitwise."""
    A = x01.scale(fake[2], "A_epoch_z")[:6]
    ref, rate = core.reservoir_bsc6(A, 0.9)
    got, rate2 = x01.reservoir_counts(A, 0.9, core.T_START, core.T_END, core.BSC_N_BINS, t_stop=256)
    assert np.array_equal(ref, got) and rate == rate2
    enc, rate3 = x01.encode(A, "R1_reservoir_bibm")
    assert np.array_equal(enc, ref) and rate3 == rate


def test_r2_never_sees_post_stimulus_samples(fake, x01):
    A = x01.scale(fake[2], "A_epoch_z")[:6]
    code, rate = x01.encode(A, "R2_reservoir_onset")
    assert code.shape == (6, 34, 1536) and code.max() <= 7 and 0 <= rate <= 1
    changed = A.copy(); changed[:, 51:, :] = 123.0                           # rewrite everything after onset
    code2, rate2 = x01.encode(changed, "R2_reservoir_onset")
    assert np.array_equal(code, code2) and rate == rate2
    changed = A.copy(); changed[:, 50, :] += 1.0                             # the last pre-onset sample does count
    assert not np.array_equal(code, x01.encode(changed, "R2_reservoir_onset")[0])


def test_simple_encoders(fake, x01):
    A = x01.scale(fake[2], "A_epoch_z")
    P, r = x01.encode(A, "P_prestim_mean")
    assert r is None and np.array_equal(P, A[:, 9:51, :].mean(axis=1)) and P.shape == (30, 34)
    E, r = x01.encode(A, "E_erp_windows")
    assert r is None and np.array_equal(E, core.erp_window_means(A).reshape(30, -1))


def test_protocol_pieces(fake, x01):
    _, _, X, y, g, _, _ = fake
    folds = x01.partitions(y, g, core.SEEDS)
    assert len(folds) == 25
    for _, tr, te in folds:
        assert not set(g[tr]) & set(g[te])
    F = core.erp_window_means(x01.scale(X, "A_epoch_z")).reshape(30, -1)
    acc = np.zeros((30, 3))
    for seed, tr, te in folds:
        acc[te] += core.readout_proba(F[tr], y[tr], F[te], seed)
    assert np.array_equal(x01.oof_predictions(F, y, folds), np.argmax(acc, axis=1))
    B, _ = core.reservoir_bsc6(x01.scale(X, "A_epoch_z"), 0.9)
    seed, tr, te = folds[0]
    Xtr, Xte = x01.fold_features(B, tr, te)
    from sklearn.decomposition import PCA
    pca = PCA(n_components=64, random_state=42).fit(B[tr].reshape(-1, 1536))
    assert Xtr.shape == (len(tr), 34 * 64)
    assert np.array_equal(Xte, pca.transform(B[te].reshape(-1, 1536)).reshape(len(te), -1))


def test_end_to_end_on_synthetic_files(fake, x01, tmp_path, monkeypatch):
    """main() from files to JSON, with reduced resampling. Output goes to a temporary directory."""
    d, _, _, _, _, _, pkl = fake
    monkeypatch.setenv("SHAPE_RAW_DIR", str(d)); monkeypatch.setenv("ARSPI_SHAPE_FEATURES", str(pkl))
    monkeypatch.setattr(x01, "OUT_DIR", tmp_path / "out")
    real_run = x01.run
    monkeypatch.setattr(x01, "run", lambda X, y, g: real_run(X, y, g, seeds=[42, 43], n_boot=60, n_perm=5, log=lambda *_: None))
    assert x01.main() == 0
    text = (tmp_path / "out" / "x01_scaling.json").read_text()
    out = json.loads(text)
    assert out["step0"]["passed"] and out["provenance"]["experiment_id"] == "X01-2026-11"
    assert set(out["BA"]) == set(x01.ENCODERS)
    for enc in x01.ENCODERS:
        assert set(out["BA"][enc]) == set(x01.SCALINGS)
        assert set(out["paired_differences"][enc]) == {"A_epoch_z_minus_B_pre_sd", "A_epoch_z_minus_C_none"}
        for sc in x01.SCALINGS:
            lo, hi = out["BA"][enc][sc]["ci95"]
            assert 0 <= lo <= out["BA"][enc][sc]["BA"] <= hi <= 1
    assert set(out["firing_rate"]) == {"R1_reservoir_bibm", "R2_reservoir_onset"}
    null = out["permutation_null"]
    assert null["n_permutations"] == 5 and null["null_p2.5"] <= null["null_mean"] <= null["null_p97.5"]
    # privacy: no subject identifier and no per-observation row in the output
    for sid in ("003", "011", "045", "101", "130", "151"):
        assert f'"{sid}"' not in text
    assert "subjects" not in text.replace("n_subjects", "").replace("excluded_subjects", "")


def test_step0_failure_stops_before_step1(fake, x01, tmp_path, monkeypatch):
    d, _, _, _, _, _, pkl = fake
    with open(pkl, "rb") as fh:
        bad = pickle.load(fh)
    bad["y"] = (bad["y"] + 1) % 3
    p = tmp_path / "wrong_labels.pkl"; pickle.dump(bad, open(p, "wb"))
    monkeypatch.setenv("SHAPE_RAW_DIR", str(d)); monkeypatch.setenv("ARSPI_SHAPE_FEATURES", str(p))
    monkeypatch.setattr(x01, "OUT_DIR", tmp_path / "out")
    monkeypatch.setattr(x01, "run", lambda *a, **k: pytest.fail("Step 1 ran after a failed Step 0"))
    with pytest.raises(SystemExit):
        x01.main()
    out = json.loads((tmp_path / "out" / "x01_scaling.json").read_text())
    assert out["step0"]["passed"] is False and out["step0"]["labels_match"] is False and "BA" not in out
