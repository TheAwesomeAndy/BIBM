#!/usr/bin/env python3
"""Extension experiment X01-2026-11: does the reservoir's balanced accuracy depend on the
per-epoch z-scoring of its input?

This is an extension experiment (docs/EXPERIMENT_REGISTRY.md). It is not part of the
accepted BIBM 2026 paper and writes nothing under outputs/aggregate/.

Design (fixed in advance by the author; nothing here is tuned to a result)

  Data     Raw SHAPE epochs SHAPE_Community_<id>_IAPS{Neg,Neu,Pos}_BC.txt, 1229 samples x 34
           channels at 1024 Hz, baseline-corrected over the first 205 samples. Subject 127 is
           excluded; subjects need all three condition files. Labels Neg=0, Neu=1, Pos=2.
           Analysed signal = raw[0:1024:4] (256 samples, onset at sample 51).

  Step 0   Reproduction check. Scaling A must equal the X_ds of the pickle the paper used, in
           the same subject order with the same labels. Otherwise the run stops.

  Step 1   Four scalings of the analysed signal, per epoch and channel:
             A epoch_z  z-score over all 256 samples
             B pre_sd   divide by the SD of samples [0, 51); no mean subtraction
             C none     no scaling
             D post_z   z-score with the mean and SD of samples [51, 256)

  Step 2   Encoders, built from analysis/core.py without modifying it:
             R1 reservoir_bibm   core.reservoir_bsc6 at rho 0.9 (window [10, 70))
             R2 reservoir_onset  same reservoir, simulated for samples [0, 51) only, spike counts
                                 over [9, 51) in 6 bins of 7 samples
             P  prestim_mean     channel mean over samples [9, 51)
             E  erp_windows      core.erp_window_means

  Step 3   Protocol of the accepted paper: StratifiedGroupKFold(5, shuffle), seeds 42-46,
           subject groups, train-only PCA-64 for R1/R2 (one basis shared across electrodes),
           core.fit_readout, out-of-fold probabilities summed over the five partitions,
           subject-level bootstrap (4000 resamples), paired differences A-B and A-C.

  Step 4   Within-subject label-permutation null for R1 under B: 50 permutations, partition
           seed 42 only.

Usage
  SHAPE_RAW_DIR=<dir with the .txt files> ARSPI_SHAPE_FEATURES=<pickle> \\
      python experiments/X01-2026-11/run_x01.py

Privacy: reads restricted data locally. Writes one aggregate JSON to
outputs/extensions/X01-2026-11/. No subject identifier and no subject-level row is written.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import re
import subprocess
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedGroupKFold

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis"))
import core  # noqa: E402  (unchanged accepted implementation)
import reanalysis_subject_bootstrap as RB  # noqa: E402  (subject_bootstrap, paired_diff_ci)

EXPERIMENT_ID = "X01-2026-11"
OUT_DIR = ROOT / "outputs" / "extensions" / EXPERIMENT_ID

# --- data ---
RAW_SAMPLES, N_CH = 1229, 34
EXCLUDED_SUBJECTS = ("127",)
CONDITIONS = (("Neg", 0), ("Neu", 1), ("Pos", 2))
DS_STOP, DS_STEP = 1024, 4              # analysed signal = raw[0:1024:4]
ONSET = 51                              # stimulus onset, in analysed samples
FILE_RE = re.compile(r"^SHAPE_Community_(.+)_IAPS(Neg|Neu|Pos)_BC\.txt$")
STEP0_TOL = 1e-5                        # max |difference| accepted as "equals X_ds"

# --- design ---
SCALINGS = ("A_epoch_z", "B_pre_sd", "C_none", "D_post_z")
ENCODERS = ("R1_reservoir_bibm", "R2_reservoir_onset", "P_prestim_mean", "E_erp_windows")
RHO = 0.9
R2_T_START, R2_T_END, R2_BINS = 9, ONSET, 6     # 42 samples, 6 bins of 7
PRESTIM = (9, ONSET)
N_PERM, PERM_RNG_SEED, PERM_PARTITION_SEED = 50, 2026, 42


class Step0Mismatch(SystemExit):
    """Raised when the rebuilt signal does not reproduce the paper's X_ds."""


# ---------------------------------------------------------------- data loading

def _subject_key(sid: str):
    return (0, int(sid)) if sid.isdigit() else (1, sid)


def _norm_id(sid) -> str:
    """Subject IDs compare equal across '007', 7 and 7.0 (file names against stored arrays)."""
    t = str(sid).strip()
    try:
        return str(int(float(t)))
    except ValueError:
        return t


def _read_epoch(path: Path) -> np.ndarray:
    with open(path, encoding="utf-8", errors="replace") as fh:
        first = fh.readline()
    arr = np.loadtxt(path, delimiter="," if "," in first else None, dtype=np.float64)
    if arr.shape != (RAW_SAMPLES, N_CH):
        raise SystemExit(f"unexpected raw epoch shape {arr.shape} (expected {(RAW_SAMPLES, N_CH)}) "
                         f"in a {FILE_RE.pattern} file; not guessing an orientation")
    return arr


def load_raw(raw_dir: str | os.PathLike):
    """Return raw (N, 1229, 34), y (N,), groups (N,) and an order-independent data checksum.

    Subjects are taken in ascending ID order (numeric where the ID is a number) and, within a
    subject, in the order Neg, Neu, Pos.
    """
    files: dict[str, dict[str, Path]] = {}
    for p in Path(raw_dir).rglob("SHAPE_Community_*_BC.txt"):
        m = FILE_RE.match(p.name)
        if m:
            files.setdefault(m.group(1), {})[m.group(2)] = p
    for sid in EXCLUDED_SUBJECTS:
        files.pop(sid, None)
    complete = sorted((s for s, f in files.items() if len(f) == len(CONDITIONS)), key=_subject_key)
    if not complete:
        raise SystemExit(f"no complete subjects found under {raw_dir}")
    raw, y, g, digests = [], [], [], []
    for sid in complete:
        for cond, label in CONDITIONS:
            path = files[sid][cond]
            digests.append(hashlib.sha256(path.read_bytes()).hexdigest())
            raw.append(_read_epoch(path)); y.append(label); g.append(sid)
    checksum = hashlib.sha256("".join(sorted(digests)).encode()).hexdigest()
    info = {"n_subjects_found": len(files), "n_subjects_complete": len(complete),
            "n_observations": len(y), "raw_files_sha256_of_sorted_sha256": checksum}
    return np.stack(raw), np.asarray(y), np.asarray(g), info


def analysed_signal(raw: np.ndarray) -> np.ndarray:
    return raw[:, 0:DS_STOP:DS_STEP, :]                         # (N, 256, 34)


# -------------------------------------------------------------------- scalings

def _checked_sd(sd: np.ndarray, name: str) -> np.ndarray:
    n_zero = int((sd == 0).sum())
    if n_zero:
        raise SystemExit(f"scaling {name}: {n_zero} epoch-channel traces have zero SD; the design "
                         f"does not say how to scale them, so the run stops")
    return sd


def scale(X: np.ndarray, name: str) -> np.ndarray:
    """Scale each epoch and channel along time. SDs are population SDs (ddof = 0)."""
    if name == "A_epoch_z":
        return (X - X.mean(axis=1, keepdims=True)) / _checked_sd(X.std(axis=1, keepdims=True), name)
    if name == "B_pre_sd":
        return X / _checked_sd(X[:, :ONSET, :].std(axis=1, keepdims=True), name)
    if name == "C_none":
        return X.copy()
    if name == "D_post_z":
        post = X[:, ONSET:, :]
        return (X - post.mean(axis=1, keepdims=True)) / _checked_sd(post.std(axis=1, keepdims=True), name)
    raise ValueError(name)


# ---------------------------------------------------------------------- step 0

def step0(X: np.ndarray, y: np.ndarray, g: np.ndarray, pickle_path: str | os.PathLike) -> dict:
    """Compare scaling A with the X_ds of the paper's pickle. Stops the run on a mismatch."""
    with open(pickle_path, "rb") as fh:
        d = pickle.load(fh)
    X_ref = np.asarray(d["X_ds"], float); y_ref = np.asarray(d["y"]); g_ref = np.asarray(d["subjects"])
    res = {"pickle_sha256": hashlib.sha256(Path(pickle_path).read_bytes()).hexdigest(),
           "n_observations_rebuilt": int(len(y)), "n_observations_pickle": int(len(y_ref)),
           "n_subjects_rebuilt": int(np.unique(g).size), "n_subjects_pickle": int(np.unique(g_ref).size),
           "tolerance": STEP0_TOL}
    same_shape = X_ref.shape == X.shape
    res["shape_match"] = bool(same_shape)
    res["subject_order_match"] = bool(same_shape and [_norm_id(s) for s in g] == [_norm_id(s) for s in g_ref])
    res["labels_match"] = bool(same_shape and np.array_equal(y, y_ref))
    A = scale(X, "A_epoch_z")
    if same_shape:
        res["max_abs_difference"] = float(np.abs(A - X_ref).max())
        # diagnostic only, never used to proceed: the same comparison with the sample SD
        sd1 = X.std(axis=1, ddof=1, keepdims=True)
        res["diagnostic_max_abs_difference_ddof1"] = float(np.abs((X - X.mean(axis=1, keepdims=True)) / sd1 - X_ref).max())
    else:
        res["max_abs_difference"] = None
    res["passed"] = bool(same_shape and res["subject_order_match"] and res["labels_match"]
                         and res["max_abs_difference"] <= STEP0_TOL)
    return res


# -------------------------------------------------------------------- encoders

def reservoir_counts(X: np.ndarray, rho: float, t_start: int, t_end: int, n_bins: int, t_stop: int):
    """Spike-bin code from the accepted reservoir (core.init_weights, core.lif_step).

    The simulation starts from rest and runs for samples [0, t_stop); counts are taken over
    [t_start, t_end) in n_bins equal bins. With (10, 70, 6, 256) this is core.reservoir_bsc6
    (checked bitwise in tests/test_x01_extension.py).
    """
    N, _, n_ch = X.shape; C = N * n_ch
    if (t_end - t_start) % n_bins:
        raise ValueError("window is not divisible into equal bins")
    S = np.transpose(X, (1, 0, 2)).reshape(X.shape[1], C)
    W_in, W = core.init_weights(rho); win0 = W_in[:, 0][:, None]
    mem = np.zeros((core.N_RES, C)); spk = np.zeros((core.N_RES, C))
    counts = np.zeros((core.N_RES, n_bins, C), dtype=np.float32)
    binw = (t_end - t_start) // n_bins
    for t in range(t_stop):
        mem, spk = core.lif_step(mem, spk, win0 * S[t][None, :], W)
        if t_start <= t < t_end:
            counts[:, (t - t_start) // binw, :] += spk
    rate = float(counts.sum() / (core.N_RES * C * (t_end - t_start)))
    return counts.reshape(core.N_RES * n_bins, C).T.reshape(N, n_ch, -1), rate


def encode(X: np.ndarray, encoder: str):
    """Return (features, firing rate or None). Reservoir features are (N, 34, 1536) spike codes."""
    if encoder == "R1_reservoir_bibm":
        return core.reservoir_bsc6(X, RHO)
    if encoder == "R2_reservoir_onset":
        return reservoir_counts(X, RHO, R2_T_START, R2_T_END, R2_BINS, t_stop=ONSET)
    if encoder == "P_prestim_mean":
        return X[:, PRESTIM[0]:PRESTIM[1], :].mean(axis=1), None
    if encoder == "E_erp_windows":
        return core.erp_window_means(X).reshape(X.shape[0], -1), None
    raise ValueError(encoder)


# -------------------------------------------------------------------- protocol

def partitions(y, g, seeds):
    out = []
    for seed in seeds:
        cv = StratifiedGroupKFold(core.N_FOLDS, shuffle=True, random_state=seed)
        out += [(seed, tr, te) for tr, te in cv.split(np.zeros((len(y), 1)), y, groups=g)]
    return out


def fold_features(F: np.ndarray, tr, te):
    """Train-only PCA-64 for a spike code (one basis shared across electrodes); identity otherwise."""
    if F.ndim == 2:
        return F[tr], F[te]
    D = F.shape[2]
    pca = PCA(n_components=core.PCA_K, random_state=core.SEED).fit(F[tr].reshape(-1, D))
    return (pca.transform(F[tr].reshape(-1, D)).reshape(len(tr), -1),
            pca.transform(F[te].reshape(-1, D)).reshape(len(te), -1))


def oof_predictions(F, y, folds, y_fit=None):
    """Out-of-fold probabilities summed over partitions, then argmax."""
    y_fit = y if y_fit is None else y_fit
    classes = np.unique(y)
    acc = np.zeros((len(y), classes.size))
    for seed, tr, te in folds:
        Xtr, Xte = fold_features(F, tr, te)
        acc[te] += core.readout_proba(Xtr, y_fit[tr], Xte, seed)
    return classes[np.argmax(acc, axis=1)]


def permutation_null(F, y, g, n_perm=N_PERM, partition_seed=PERM_PARTITION_SEED, rng_seed=PERM_RNG_SEED):
    """Within-subject label permutation on one partition. PCA is label-free, so it is fitted once."""
    folds = partitions(y, g, [partition_seed])
    feats = [fold_features(F, tr, te) for _, tr, te in folds]
    classes = np.unique(y)

    def ba(labels):
        acc = np.zeros((len(y), classes.size))
        for (seed, tr, te), (Xtr, Xte) in zip(folds, feats, strict=True):
            acc[te] += core.readout_proba(Xtr, labels[tr], Xte, seed)
        return float(balanced_accuracy_score(labels, classes[np.argmax(acc, axis=1)]))

    observed = ba(y)
    rng = np.random.default_rng(rng_seed)
    null = []
    for _ in range(n_perm):
        yp = y.copy()
        for s in np.unique(g):
            idx = np.where(g == s)[0]; yp[idx] = rng.permutation(y[idx])
        null.append(ba(yp))
    return {"encoder": "R1_reservoir_bibm", "scaling": "B_pre_sd", "partition_seed": partition_seed,
            "n_permutations": n_perm, "rng_seed": rng_seed, "observed_BA_single_partition": observed,
            "null_mean": float(np.mean(null)), "null_p2.5": float(np.percentile(null, 2.5)),
            "null_p97.5": float(np.percentile(null, 97.5))}


# ------------------------------------------------------------------ experiment

def run(X, y, g, seeds=None, n_boot=core.N_BOOT, n_perm=N_PERM, log=print):
    """Steps 1 to 4 on an analysed signal X (N, 256, 34). Returns the aggregate result dict."""
    seeds = list(core.SEEDS) if seeds is None else list(seeds)
    folds = partitions(y, g, seeds)
    preds, res = {}, {"BA": {}, "firing_rate": {}, "paired_differences": {}}
    null_features = None
    for sc in SCALINGS:
        Xs = scale(X, sc)
        for enc in ENCODERS:
            t0 = time.time()
            F, rate = encode(Xs, enc)
            if rate is not None:
                res["firing_rate"].setdefault(enc, {})[sc] = rate
            if (enc, sc) == ("R1_reservoir_bibm", "B_pre_sd"):
                null_features = F
            preds[(enc, sc)] = oof_predictions(F, y, folds)
            log(f"[X01] {enc} / {sc}: done ({time.time() - t0:.0f}s)")
    for enc in ENCODERS:
        pt, ci, _ = RB.subject_bootstrap(y, g, {sc: preds[(enc, sc)] for sc in SCALINGS}, n_boot=n_boot)
        res["BA"][enc] = {sc: {"BA": float(pt[sc]), "ci95": [float(ci[sc][0]), float(ci[sc][1])]} for sc in SCALINGS}
        res["paired_differences"][enc] = {}
        for other in ("B_pre_sd", "C_none"):
            m, lo, hi, _ = RB.paired_diff_ci(y, g, preds[(enc, "A_epoch_z")], preds[(enc, other)], n_boot=n_boot)
            res["paired_differences"][enc][f"A_epoch_z_minus_{other}"] = {"mean_diff": m, "ci95": [lo, hi]}
    res["permutation_null"] = permutation_null(null_features, y, g, n_perm=n_perm)
    return res


def provenance(raw_info: dict, pickle_sha: str, seeds, n_boot) -> dict:
    import scipy
    import sklearn

    def git(*args):
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()

    return {"experiment_id": EXPERIMENT_ID, "status": "extension; not part of the accepted BIBM 2026 paper",
            "git_commit": git("rev-parse", "HEAD"),
            "working_tree_dirty": bool(git("status", "--porcelain", "--", "analysis", "experiments")),
            "utc_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "versions": {"python": sys.version.split()[0], "numpy": np.__version__,
                         "scikit-learn": sklearn.__version__, "scipy": scipy.__version__},
            "data": {**raw_info, "pickle_sha256": pickle_sha},
            "parameters": {"rho": RHO, "scalings": list(SCALINGS), "encoders": list(ENCODERS),
                           "sd_ddof": 0, "onset_sample": ONSET, "downsample": f"raw[0:{DS_STOP}:{DS_STEP}]",
                           "R1_window": [core.T_START, core.T_END], "R1_bins": core.BSC_N_BINS,
                           "R2_window": [R2_T_START, R2_T_END], "R2_bins": R2_BINS, "R2_simulated_samples": ONSET,
                           "prestim_window": list(PRESTIM), "erp_windows_ms": core.ERP_WINDOWS_MS,
                           "pca_components": core.PCA_K, "seeds": list(seeds), "n_folds": core.N_FOLDS,
                           "n_boot": n_boot, "bootstrap_seeds": {"subject_bootstrap": 12345, "paired_diff_ci": 999},
                           "excluded_subjects": list(EXCLUDED_SUBJECTS), "step0_tolerance": STEP0_TOL}}


def main() -> int:
    raw_dir = os.environ.get("SHAPE_RAW_DIR"); pkl = os.environ.get("ARSPI_SHAPE_FEATURES")
    if not raw_dir or not pkl:
        raise SystemExit("set SHAPE_RAW_DIR (raw .txt epochs) and ARSPI_SHAPE_FEATURES (the paper's pickle)")
    raw, y, g, raw_info = load_raw(raw_dir)
    X = analysed_signal(raw)
    print(f"[X01] {raw_info['n_subjects_complete']} subjects, {len(y)} observations, signal {X.shape}")
    s0 = step0(X, y, g, pkl)
    print(f"[X01 step 0] max |difference| = {s0['max_abs_difference']}; subject order match = "
          f"{s0['subject_order_match']}; labels match = {s0['labels_match']}; passed = {s0['passed']}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = {"provenance": provenance(raw_info, s0["pickle_sha256"], core.SEEDS, core.N_BOOT), "step0": s0}
    if not s0["passed"]:
        out["stopped"] = "Step 0 did not reproduce the paper's X_ds; Steps 1 to 4 were not run."
        with open(OUT_DIR / "x01_scaling.json", "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2)
        raise Step0Mismatch("Step 0 failed: stopping before Step 1 (see x01_scaling.json)")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        out.update(run(X, y, g))
    out["readout_convergence_warnings"] = sum(issubclass(w.category, ConvergenceWarning) for w in caught)
    with open(OUT_DIR / "x01_scaling.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"[X01] wrote {OUT_DIR / 'x01_scaling.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
