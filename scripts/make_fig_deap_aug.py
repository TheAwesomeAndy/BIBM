#!/usr/bin/env python3
"""Fig. 4 (camera-ready).

(a) External check on DEAP (scripts/deap_replication.py): band-power balanced accuracy versus
    channels removed under zero, train-mean and kNN fill, with subject-level 95% CIs; the
    clean level and chance are marked.
(b) Training effect (scripts/experiment_eegnet_signal.py): EEGNet with and without train-time
    augmentation under the shared signal-level conditions (clean, 5 dB noise, +/-50 ms
    jitter, 30% electrodes removed), subject-level 95% CIs.
Fill rules / models differ by marker, line style and hatch, not color alone. Reads only
aggregate JSON.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "outputs/aggregate"
OUT = ROOT / "manuscript/figures/imported/fig_deap_aug.pdf"
plt.rcParams.update({"font.size": 9, "axes.linewidth": 0.8, "pdf.fonttype": 42, "ps.fonttype": 42})


def main():
    deap = json.load(open(A / "deap_replication_v2.json"))["BandPower"]
    e3 = json.load(open(A / "e3_eegnet_signal.json"))["BA"]
    fig, ax = plt.subplots(1, 2, figsize=(7.1, 2.7))

    rates = [10, 30, 50]; keys = ["0.10", "0.30", "0.50"]
    sty = {"zero": ("--", "o", "zero fill"), "mean": ("-.", "s", "mean fill"), "knn": ("-", "^", "kNN fill")}
    for fill, (ls, mk, lab) in sty.items():
        v = np.array([deap[k][fill]["BA_mean_over_folds"] for k in keys])
        lo = np.array([deap[k][fill]["subject_ci95"][0] for k in keys])
        hi = np.array([deap[k][fill]["subject_ci95"][1] for k in keys])
        ax[0].errorbar(rates, v, yerr=[v - lo, hi - v], color="black", ls=ls, marker=mk, ms=5,
                       lw=1.3, capsize=2.5, mfc="white" if fill == "zero" else "black", label=lab)
    clean = deap["clean"]["BA_mean_over_folds"]
    ax[0].axhline(clean, color="0.45", ls=(0, (1, 1)), lw=1.0)
    ax[0].text(10.3, clean + 0.004, f"clean {clean:.3f}", fontsize=6.6, color="0.3")
    ax[0].axhline(0.5, color="0.7", ls=(0, (1, 1)), lw=0.9)
    ax[0].text(50, 0.503, "chance", fontsize=6.5, color="0.45", ha="right")
    ax[0].set_xlabel("Channels removed (%)"); ax[0].set_ylabel("Balanced accuracy")
    ax[0].set_title("(a) DEAP: fill rule under channel loss", fontsize=8.5)
    ax[0].set_xticks(rates); ax[0].legend(frameon=False, fontsize=6.8, loc="lower left")
    ax[0].grid(True, color="0.92", lw=0.6); ax[0].set_axisbelow(True)

    conds = [("remove_0.0", "Clean"), ("amp_5dB", "Noise 5 dB"), ("jitter_50ms", r"Jitter $\pm$50 ms"),
             ("remove_0.3", "30% removed")]
    x = np.arange(len(conds)); w = 0.36
    for j, (m, face, hatch, lab) in enumerate((("EEGNet", "#dddddd", "..", "EEGNet"),
                                              ("EEGNet+aug", "#555555", "xx", "EEGNet + aug."))):
        v = np.array([e3[c][m]["BA"] for c, _ in conds])
        lo = np.array([e3[c][m]["ci95"][0] for c, _ in conds]); hi = np.array([e3[c][m]["ci95"][1] for c, _ in conds])
        ax[1].bar(x + (j - 0.5) * w, v, w, yerr=[v - lo, hi - v], capsize=2, color=face,
                  edgecolor="black", lw=0.6, hatch=hatch, label=lab)
    ax[1].axhline(1 / 3, color="0.5", ls=(0, (3, 2)), lw=0.9)
    ax[1].set_xticks(x); ax[1].set_xticklabels([c[1] for c in conds], fontsize=7.2)
    ax[1].set_ylabel("Balanced accuracy"); ax[1].set_ylim(0.30, 0.82)
    ax[1].set_title("(b) Training effect (EEGNet, signal level)", fontsize=8.5)
    ax[1].legend(frameon=False, fontsize=6.8, loc="upper right")
    ax[1].grid(True, axis="y", color="0.92", lw=0.6); ax[1].set_axisbelow(True)

    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight")
    print(f"[fig] wrote {OUT}")


if __name__ == "__main__":
    main()
