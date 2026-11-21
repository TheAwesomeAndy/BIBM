"""The committed EEGNet (E3) and DEAP runs: outputs against the manuscript and the audit.

Both experiments were run by the author for the accepted paper. Their outputs
are committed (outputs/aggregate/e3_eegnet_signal.json and
deap_replication_v2.json) and the camera-ready audit records a deterministic
rerun of E3 and a reproduction of every DEAP value (docs/CODE_AUDIT.md,
section 3). These tests pin those outputs to what the paper states. They do
not re-run either experiment.
"""
from __future__ import annotations

import re

import pytest


def _f(x, nd=3):
    return f"{x:.{nd}f}"


@pytest.fixture(scope="module")
def e3(aggregate):
    return aggregate("e3_eegnet_signal.json")


@pytest.fixture(scope="module")
def deap(aggregate):
    return aggregate("deap_replication_v2.json")


# ----------------------------------------------------------------- EEGNet (E3)

def test_e3_structure_and_protocol(e3):
    conds = ["remove_0.0", "remove_0.1", "remove_0.3", "remove_0.5", "amp_5dB", "jitter_50ms"]
    assert list(e3["BA"]) == conds
    for c in conds:
        assert list(e3["BA"][c]) == ["EEGNet", "EEGNet+aug", "ERP-window"]
    p = e3["protocol"]
    for needle in ("EEGNet-8,2 (F1=8,D=2,F2=16,k=64,dropout=0.25)", "Adam lr=0.001", "80 epochs", "batch 64",
                   "StratifiedGroupKFold(5) x seeds 42-46", "train-only per-channel z-score", "n_boot=4000"):
        assert needle in p


def test_e3_shares_draws_with_fixed_encoders(e3, aggregate):
    """E3 recomputes ERP-window under its own removals; it must equal E4 exactly (same draws)."""
    e4 = aggregate("e4_signal_perturbations.json")["BA"]
    for c3, c4 in (("remove_0.0", "clean"), ("remove_0.1", "remove_0.1"), ("remove_0.3", "remove_0.3"),
                   ("remove_0.5", "remove_0.5"), ("amp_5dB", "amp_5dB"), ("jitter_50ms", "jitter_50ms")):
        assert e3["BA"][c3]["ERP-window"]["BA"] == e4[c4]["ERP-window"]["BA"]


def test_e3_training_effect_sentence(e3, manuscript_tex):
    """Results, 'Training effect' paragraph: every number against the committed run."""
    para = next(ln for ln in manuscript_tex.splitlines() if ln.startswith("\\emph{Training effect.}"))
    loss = e3["paired_clean_minus_condition"]
    gain = e3["paired_aug_minus_unaug"]
    lead = e3["paired_minus_ERPwindow"]

    assert f"loses ${_f(loss['remove_0.3']['EEGNet']['mean_diff'])}$~BA at $30\\%$ removal" in para
    assert f"and ${_f(loss['remove_0.5']['EEGNet']['mean_diff'])}$ at $50\\%$" in para
    assert (f"to ${_f(loss['remove_0.3']['EEGNet+aug']['mean_diff'])}$ and "
            f"${_f(loss['remove_0.5']['EEGNet+aug']['mean_diff'])}$") in para
    for c in ("remove_0.3", "remove_0.5"):
        g = gain[c]
        assert f"$+{_f(g['mean_diff'])}$ ($[+{_f(g['ci95'][0])},+{_f(g['ci95'][1])}]$)" in para
    g0 = gain["remove_0.0"]
    assert f"$[{g0['ci95'][0]:+.3f},{g0['ci95'][1]:+.3f}]$" in para and abs(g0["mean_diff"]) < 0.0005
    # "cuts these losses by more than half"
    for c in ("remove_0.3", "remove_0.5"):
        assert loss[c]["EEGNet+aug"]["mean_diff"] < 0.5 * loss[c]["EEGNet"]["mean_diff"]
    # "paired lead over ERP-window +0.08 to +0.20, every CI excluding zero"
    leads = [v for c in lead.values() for v in c.values()]
    assert len(leads) == 12
    assert (round(min(v["mean_diff"] for v in leads), 2), round(max(v["mean_diff"] for v in leads), 2)) == (0.08, 0.20)
    assert all(v["ci95"][0] > 0 for v in leads)
    assert "$+0.08$ to $+0.20$" in para
    # "the most accurate encoder in every condition"
    for c, row in e3["BA"].items():
        assert min(row["EEGNet"]["BA"], row["EEGNet+aug"]["BA"]) > row["ERP-window"]["BA"]


def test_legacy_eegnet_outputs_match_cover_note(aggregate, root):
    """The June runs (eegnet.json, eegnet_aug.json) are the 'submitted' column of the cover note."""
    old, old_aug = aggregate("eegnet.json"), aggregate("eegnet_aug.json")
    note = (root / "manuscript" / "cover_note.md").read_text(encoding="utf-8")
    assert _f(old["clean"]["BA"][0]) == "0.711" and "0.711 / 0.616 / 0.485 / 0.463" in note
    assert (_f(old["drop"]["BA"][0]), _f(old_aug["drop"]["BA"][0])) == ("0.554", "0.674")
    assert "0.554 / 0.674 | 0.660 / 0.703" in note


# ------------------------------------------------------------------------ DEAP

def test_deap_structure(deap):
    bp = deap["BandPower"]
    assert list(bp) == ["clean", "0.10", "0.30", "0.50"]
    for rate in ("0.10", "0.30", "0.50"):
        assert list(bp[rate]) == ["zero", "mean", "knn"]
    cells = [bp["clean"]] + [bp[r][f] for r in ("0.10", "0.30", "0.50") for f in ("zero", "mean", "knn")]
    assert len(cells) == 10 and all(c["n_subjects"] == 32 for c in cells)
    for c in cells:
        assert c["BA_mean_over_folds"] == pytest.approx(c["subject_mean_BA"], abs=1e-12)
        assert c["subject_ci95"][0] < c["subject_mean_BA"] < c["subject_ci95"][1]
    assert "WITHIN-subject" in deap["protocol"] and "4-8, 8-12, 12-30, 30-45 Hz" in deap["protocol"]


def test_deap_audit_anchors(deap):
    """docs/CODE_AUDIT.md, section 3: the reproduced column, to four decimals."""
    bp = deap["BandPower"]
    got = [bp["clean"]["BA_mean_over_folds"], bp["0.10"]["zero"]["BA_mean_over_folds"]] + [
        bp["0.30"][f]["BA_mean_over_folds"] for f in ("zero", "mean", "knn")]
    assert [round(v, 4) for v in got] == [0.6390, 0.5808, 0.5397, 0.6207, 0.6381]


def test_deap_matches_original_run(deap, aggregate):
    """All ten values against the earlier run (deap_replication.json): max |difference| 4.8e-05."""
    old = aggregate("deap_replication.json")["BA"]["BandPower(NC)"]
    new = deap["BandPower"]
    diffs = [abs(old["clean"][0] - new["clean"]["BA_mean_over_folds"])]
    diffs += [abs(old[r][f] - new[r][f]["BA_mean_over_folds"])
              for r in ("0.10", "0.30", "0.50") for f in ("zero", "mean", "knn")]
    assert len(diffs) == 10 and max(diffs) < 5e-5
    assert round(max(diffs), 6) == 4.8e-05


def test_deap_results_paragraph(deap, manuscript_tex):
    """Sec. V-D: every number against the committed run."""
    para = next(ln for ln in manuscript_tex.splitlines() if ln.startswith("As an external check of the imputation effect"))
    bp = deap["BandPower"]; z, m, k = (bp["0.30"][f] for f in ("zero", "mean", "knn"))
    assert f"BA ${_f(z['subject_mean_BA'])}$ under zero-imputation ($95\\%$ CI $[{_f(z['subject_ci95'][0])},{_f(z['subject_ci95'][1])}]$)" in para
    assert f"${_f(m['subject_mean_BA'])}$ $[{_f(m['subject_ci95'][0])},{_f(m['subject_ci95'][1])}]$ under mean" in para
    assert f"${_f(k['subject_mean_BA'])}$ $[{_f(k['subject_ci95'][0])},{_f(k['subject_ci95'][1])}]$ under $k$NN" in para
    clean = bp["clean"]["subject_mean_BA"]
    assert f"Against clean BA ${_f(clean)}$" in para
    assert "a $0.10$ BA loss" in para and _f(clean - z["subject_mean_BA"], 2) == "0.10"
    # "the imputation convention alone moves measured robustness by up to 0.11 BA"
    spread = max(bp[r]["knn"]["subject_mean_BA"] - bp[r]["zero"]["subject_mean_BA"] for r in ("0.10", "0.30", "0.50"))
    assert "by up to $0.11$ BA" in para and _f(spread, 2) == "0.11"
    assert "32 subjects, 40 trials each" in para


def test_fig4_caption_values(deap, manuscript_tex):
    cap = next(ln for ln in manuscript_tex.splitlines() if ln.startswith("\\caption{(a)~External check on DEAP"))
    assert f"clean BA ${_f(deap['BandPower']['clean']['subject_mean_BA'])}$" in cap
    assert re.search(r"32 subjects, within-subject binary valence", cap)
