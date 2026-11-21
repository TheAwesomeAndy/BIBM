"""Run the public analysis functions on the synthetic fixture and save every output.

Usage: python tests/equivalence_driver.py <analysis_dir> <out.npz>

tests/test_refactor_equivalence.py runs this once against the analysis/ code of
the accepted baseline commit and once against the working tree, then requires
the two result sets to be bitwise equal. The driver imports only names that
exist in the baseline, so the same file runs against both.

Bootstrap resample counts and the dropout grid are reduced, identically on both
sides, to keep the run short. That changes no code path.
"""
from __future__ import annotations

import functools
import sys
from pathlib import Path

import numpy as np


def main(analysis_dir: str, out: str) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from conftest import make_synthetic        # also puts the working tree's analysis/ on sys.path

    # The requested analysis directory must win over any other copy on the path.
    target = str(Path(analysis_dir).resolve())
    sys.path[:] = [p for p in sys.path if not (Path(p).name == "analysis" and str(Path(p).resolve()) != target)]
    sys.path.insert(0, target)

    import experiment2_rawsignal as E2S
    import experiment_camera_ready as EC
    import reanalysis_subject_bootstrap as RB
    import regen_reservoir_embedding as RG

    for mod in (E2S, EC, RB, RG):                # guard: every module comes from the requested tree
        assert Path(mod.__file__).resolve().parent == Path(target), mod.__file__
    X, y, g = make_synthetic()
    n = len(y)
    r: dict[str, np.ndarray] = {}

    def put(key, value):
        r[key] = np.asarray(value)

    # --- weights ---
    for rho in (0.0, 0.3, 0.9, 1.5):
        w_in, w = EC.weights(rho)
        put(f"EC.weights[{rho}].in", w_in); put(f"EC.weights[{rho}].rec", w)
    for name, mod in (("E2S", E2S), ("RG", RG)):
        w_in, w = mod.init_weights()
        put(f"{name}.init_weights.in", w_in); put(f"{name}.init_weights.rec", w)

    # --- reservoir codes ---
    B, rate = EC.bsc6(X, 0.9)
    put("EC.bsc6[0.9]", B); put("EC.bsc6[0.9].rate", rate)
    for rho, k in ((0.0, 3), (0.3, 6), (1.5, 3)):
        b, rt = EC.bsc6(X[:k], rho)
        put(f"EC.bsc6[{rho}]", b); put(f"EC.bsc6[{rho}].rate", rt)
    B2 = E2S.bsc6_all(X)
    put("E2S.bsc6_all", B2)
    emb, pca = RG.regen(X)
    put("RG.regen.emb", emb); put("RG.regen.evr", pca.explained_variance_ratio_)
    put("RG.validate", RG.validate(emb, y, g))
    for rho in (0.0, 0.9, 1.5):
        put(f"EC.damage[{rho}]", EC.damage(X, rho, n_drive=50))

    # --- baseline encoders ---
    band = E2S.bandpower_all(X); erp = E2S.erp_all(X)
    put("E2S.bandpower_all", band); put("E2S.erp_all", erp)
    d = {"y": y, "subjects": g, "X_ds": X, "conv_feats": band, "lsm_bsc6_pca": emb}
    for name, (F, shape) in RB.build_blocks(d).items():
        put(f"RB.build_blocks[{name}]", F); put(f"RB.build_blocks[{name}].shape", shape)

    # --- readout and out-of-fold predictions ---
    from sklearn.model_selection import StratifiedGroupKFold

    F = erp.reshape(n, -1)
    tr, te = next(StratifiedGroupKFold(5, shuffle=True, random_state=42).split(F, y, groups=g))
    put("EC.fit_pred", EC.fit_pred(F[tr], y[tr], F[te], 42))
    acc = np.zeros((n, 3))
    E2S._fit_pred(F[tr], y[tr], F[te], 42, acc, te, np.unique(y))
    put("E2S._fit_pred", acc)
    put("RB.run_oof[clean]", RB.run_oof(F, erp.shape[1:], y, g, 0.0, "zero"))
    for fill in RB.FILLS:
        put(f"RB.run_oof[0.3,{fill}]", RB.run_oof(F, erp.shape[1:], y, g, 0.3, fill))
    for frac in (0.0, 0.3):
        for name, p in E2S.oof_predictions(y, g, frac, band, erp, B2).items():
            put(f"E2S.oof_predictions[{frac}][{name}]", p)

    # --- bootstrap ---
    pred = y.copy(); pred[::4] = (pred[::4] + 1) % 3
    pt, ci, boot = RB.subject_bootstrap(y, g, {"a": pred, "b": y}, n_boot=200)
    put("RB.subject_bootstrap", [pt["a"], *ci["a"], pt["b"], *ci["b"]]); put("RB.subject_bootstrap.boot", boot["a"])
    put("RB.paired_diff_ci", RB.paired_diff_ci(y, g, pred, y, n_boot=200))
    pt2, ci2 = E2S.subj_boot(y, g, {"a": pred}, n_boot=200)
    put("E2S.subj_boot", [pt2["a"], *ci2["a"]])

    # --- train-only PCA folds and the E1 / E2 drivers ---
    cache = []
    for i, (seed, fold, tr_, te_, E, v0) in enumerate(EC.fold_embeddings(B, y, g)):
        if i < 2:
            put(f"EC.fold_embeddings[{i}].E", E); put(f"EC.fold_embeddings[{i}].v0", v0)
            put(f"EC.fold_embeddings[{i}].te", te_)
    for k, p in EC.e1_conditions(B, y, g, cache=cache).items():
        put(f"EC.e1_conditions[{k}]", p)
    put("EC.e1_conditions.cache_len", len(cache))

    RB.DROP_LEVELS = [0.3]
    orig_boot, orig_pair = RB.subject_bootstrap, RB.paired_diff_ci
    RB.subject_bootstrap = functools.partial(orig_boot, n_boot=100)
    RB.paired_diff_ci = functools.partial(orig_pair, n_boot=100)
    e2 = EC.run_e2(d, y, g, cache)

    def flatten(prefix, node):
        if isinstance(node, dict):
            for k, v in node.items():
                flatten(f"{prefix}/{k}", v)
        else:
            put(prefix, node)

    flatten("EC.run_e2", e2)
    np.savez(out, **r)
    print(f"{len(r)} outputs")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
