#!/usr/bin/env python3
"""Fig. 2: trial-averaged affective ERP data (SHAPE cohort, grand averages over 211 subjects).

(a) Grand-average waveforms per condition at the most affect-discriminative channel (largest
    |emotional - neutral| mean amplitude in the 450-800 ms late-positive-potential window);
(b) spatiotemporal map of the emotional-minus-neutral difference over all 34 channels;
(c) global field power (SD across channels) per condition.
Conditions differ by line style as well as color (grayscale-legible). Reads the restricted
SHAPE pickle locally; writes only the figure (group averages, no subject-level data).
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reanalysis_subject_bootstrap as RB  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript/figures/imported/fig_erp.pdf"
plt.rcParams.update({"font.size": 9, "axes.linewidth": 0.8, "pdf.fonttype": 42, "ps.fonttype": 42})
NAMES = {0: "negative", 1: "neutral", 2: "pleasant"}
STYLE = {0: ("#0072B2", "-"), 1: ("#7f7f7f", ":"), 2: ("#D55E00", "--")}


def main():
    d = pickle.load(open(RB._resolve_pickle(), "rb"))
    X = np.asarray(d["X_ds"], float); y = np.asarray(d["y"]).ravel()
    t = np.arange(X.shape[1]) / RB.FS * 1000                         # ms
    ga = {c: X[y == c].mean(0) for c in (0, 1, 2)}                    # (256, 34)
    lpp = (t >= 450) & (t <= 800)
    emo = (ga[0] + ga[2]) / 2
    ch = int(np.argmax(np.abs((emo - ga[1])[lpp].mean(0))))

    fig = plt.figure(figsize=(7.1, 2.15))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.15, 0.9], wspace=0.85)
    ax0 = fig.add_subplot(gs[0])
    for c in (0, 1, 2):
        col, ls = STYLE[c]
        ax0.plot(t, ga[c][:, ch], color=col, ls=ls, lw=1.6, label=NAMES[c])
    ax0.axvspan(450, 800, color="0.9", zorder=0); ax0.axhline(0, color="0.6", lw=0.6)
    ax0.set_xlabel("Time (ms)"); ax0.set_ylabel("Amplitude (a.u.)")
    ax0.set_title(f"(a) Grand-average ERP\n(ch {ch}, LPP shaded)", fontsize=8.3)
    ax0.legend(frameon=False, fontsize=6.6, loc="upper left")
    ax0.grid(True, color="0.93", lw=0.5)

    ax1 = fig.add_subplot(gs[1])
    diff = (emo - ga[1]).T                                            # (34, 256)
    vmax = np.percentile(np.abs(diff), 98)
    im = ax1.imshow(diff, aspect="auto", origin="lower", cmap="RdBu_r",
                    norm=colors.TwoSlopeNorm(0, -vmax, vmax), extent=[t[0], t[-1], 0, diff.shape[0]])
    ax1.axvline(450, color="k", lw=0.5, ls=":"); ax1.axvline(800, color="k", lw=0.5, ls=":")
    ax1.set_xlabel("Time (ms)"); ax1.set_ylabel("Channel")
    ax1.set_title("(b) Emotional $-$ neutral\nspatiotemporal map", fontsize=8.3)
    fig.colorbar(im, ax=ax1, fraction=0.040, pad=0.02).ax.tick_params(labelsize=6)

    ax2 = fig.add_subplot(gs[2])
    for c in (0, 1, 2):
        col, ls = STYLE[c]
        ax2.plot(t, ga[c].std(1), color=col, ls=ls, lw=1.5)
    ax2.axvspan(450, 800, color="0.9", zorder=0)
    ax2.set_xlabel("Time (ms)"); ax2.set_ylabel("GFP (a.u.)")
    ax2.set_title("(c) Global field\npower", fontsize=8.3)
    ax2.grid(True, color="0.93", lw=0.5)

    fig.savefig(OUT, bbox_inches="tight")
    print(f"[fig] wrote {OUT}; affect-discriminative channel = {ch}")


if __name__ == "__main__":
    main()
