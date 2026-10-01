#!/usr/bin/env python3
"""Generate the subject-level results figure from aggregate JSON (default: E2, train-only PCA).

Panel (a): channel-dropout curves (10-50%) for the three fixed encoders under
zero-fill and kNN fill, showing that the centered reservoir is nearly flat while
the non-centered encoders gain from an in-distribution fill.
Panel (b): paired subject-level difference ERP-window minus reservoir at 30%
dropout under each fill rule, with 95% CIs; the transition from a CI that
crosses zero (zero-fill) to CIs that exclude it (in-distribution fills) is the
inference behind Proposition 1.

Grayscale-legible and color-blind safe: encoders differ by marker, fills by line
style; nothing depends on color alone. Reads only aggregate JSON.
"""
import json, os
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SRC = os.environ.get("FIG_SUBJ_JSON", "outputs/aggregate/e2_trainonly_pca_fills.json")  # camera-ready: train-only PCA
J = json.load(open(ROOT / SRC))
OUT = ROOT / "manuscript/figures/imported/fig_impute_subj.pdf"

plt.rcParams.update({"font.size": 8, "axes.linewidth": 0.8, "figure.dpi": 200,
                     "pdf.fonttype": 42, "ps.fonttype": 42})
CB = {"Band-power": "#0072B2", "ERP-window": "#D55E00", "Reservoir": "#009E73"}
MK = {"Band-power": "s", "ERP-window": "o", "Reservoir": "^"}
levels = [10, 20, 30, 40, 50]

fig, (axA, axB) = plt.subplots(1, 2, figsize=(7.0, 2.7))

# Panel (a): dropout curves, zero (dashed) vs kNN (solid)
for enc in ["ERP-window", "Band-power", "Reservoir"]:
    z = [J["curve_BA"][enc]["zero"][str(l)] for l in levels]
    k = [J["curve_BA"][enc]["knn"][str(l)] for l in levels]
    axA.plot(levels, k, "-", color=CB[enc], marker=MK[enc], ms=4, lw=1.4, label=f"{enc}, kNN")
    axA.plot(levels, z, "--", color=CB[enc], marker=MK[enc], ms=4, lw=1.1, mfc="white")
axA.axhline(1/3, color="k", lw=0.7, ls=":")
axA.text(50, 1/3 + 0.006, "chance", ha="right", va="bottom", fontsize=6.5)
axA.set_xlabel("channels removed (%)"); axA.set_ylabel("balanced accuracy")
axA.set_title("(a) dropout curves: kNN (solid) vs zero (dashed)", fontsize=8)
axA.set_xticks(levels); axA.set_ylim(0.30, 0.66)
axA.legend(fontsize=6.0, loc="upper right", framealpha=0.9, handlelength=2.2)

# Panel (b): paired ERP-window minus reservoir at 30%, 95% CI by fill
pd = J["paired_ERPwindow_minus_Reservoir_30"]
fills = ["zero", "mean", "knn", "spatial"]
labels = ["zero", "mean", "kNN", "spatial"]
xs = np.arange(len(fills))
means = [pd[f]["mean_diff"] for f in fills]
los = [pd[f]["mean_diff"] - pd[f]["ci95"][0] for f in fills]
his = [pd[f]["ci95"][1] - pd[f]["mean_diff"] for f in fills]
sig = [pd[f]["ci95"][0] > 0 for f in fills]
colors = ["#555555" if not s else "#D55E00" for s in sig]
axB.axhline(0, color="k", lw=0.8)
for i in range(len(fills)):
    axB.errorbar(xs[i], means[i], yerr=[[los[i]], [his[i]]], fmt=MK["ERP-window"],
                 color=colors[i], ms=6, capsize=3, lw=1.3, mfc=colors[i])
axB.set_xticks(xs); axB.set_xticklabels(labels)
axB.set_xlabel("fill rule"); axB.set_ylabel("ERP-window $-$ reservoir (BA)")
axB.set_title("(b) paired subject-level difference at 30%", fontsize=8)
axB.set_xlim(-0.5, 3.5)
for i in range(len(fills)):   # annotation follows the data, not a fixed expectation
    axB.text(xs[i], means[i] + his[i] + 0.006, "CI excl. 0" if sig[i] else "n.s.",
             ha="center", va="bottom", fontsize=6.0)

fig.tight_layout(pad=0.4)
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, bbox_inches="tight")
print(f"[fig] wrote {OUT}")
