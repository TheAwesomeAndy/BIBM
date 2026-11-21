"""The accepted artifacts have not changed (docs/BASELINE.md)."""
from __future__ import annotations

import hashlib

import pytest


def _entries(path):
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(None, 1)
        yield digest, name.strip().lstrip("*")


def _check(root, manifest):
    bad = []
    for digest, name in _entries(root / "docs" / "baseline" / manifest):
        f = root / name
        if not f.exists():
            bad.append(f"missing: {name}")
        elif hashlib.sha256(f.read_bytes()).hexdigest() != digest:
            bad.append(f"changed: {name}")
    return bad


def test_accepted_results_unchanged(root):
    """Aggregate outputs, manuscript, PDFs and the four figures. Must always hold."""
    assert _check(root, "results.sha256") == []


def test_accepted_implementation_unchanged(root):
    """analysis/*.py at the baseline commit.

    This test is expected to fail when an approved, behavior-preserving refactor
    lands. At that point regenerate implementation.sha256 in the same commit and
    record the equivalence evidence in the memory journal (docs/BASELINE.md).
    """
    assert _check(root, "implementation.sha256") == []


def test_no_restricted_file_types_tracked(root):
    import subprocess

    out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip("not a git checkout")
    banned = (".pkl", ".pickle", ".mat", ".npy", ".npz", ".dat", ".edf", ".bdf", ".fif")
    assert [f for f in out.stdout.splitlines() if f.lower().endswith(banned)] == []


@pytest.mark.parametrize(
    "name, expected",
    [
        ("e5_controls.json", (0.487, 0.447, 0.523)),             # train-only PCA (CLAUDE.md)
        ("subject_bootstrap_reanalysis.json", (0.485, 0.447, 0.521)),  # pooled PCA sensitivity
    ],
)
def test_pca_statement_matches_outputs(aggregate, name, expected):
    """The two reservoir values quoted in CLAUDE.md, 'PCA protocol and language'."""
    d = aggregate(name)
    if name == "e5_controls.json":
        r = d["clean_metrics"]["Reservoir"]
        got = (r["BA"], *r["BA_ci95"])
    else:
        r = d["clean_BA"]["Reservoir"]
        got = (r["point"], *r["ci95"])
    assert tuple(round(v, 3) for v in got) == expected


def test_cross_script_consistency(aggregate):
    """Same quantity from independently written scripts (docs/CODE_AUDIT.md, section 3)."""
    e1 = aggregate("e1_rho_sweep.json")["BA"]["0.9"]
    e2 = aggregate("e2_trainonly_pca_fills.json")
    e4 = aggregate("e4_signal_perturbations.json")["BA"]
    e5 = aggregate("e5_controls.json")
    for name in ("Band-power", "ERP-window", "Reservoir"):
        assert e2["clean_BA"][name]["point"] == e4["clean"][name]["BA"] == e5["clean_metrics"][name]["BA"]
    assert e1["clean"]["BA"] == e2["clean_BA"]["Reservoir"]["point"]
    # reservoir, 30% signal-level removal: E1 (rho 0.9), E4, E5 (BSC6 arm)
    assert (e1["signal"]["BA"] == e4["remove_0.3"]["Reservoir"]["BA"]
            == e5["temporal_binning"]["signal30"]["BSC6"]["BA"])
    # memory entry #29: for band power and ERP-window, signal-level removal equals zero-fill
    for name in ("Band-power", "ERP-window"):
        assert e4["remove_0.3"][name]["BA"] == e2["dropout_30"]["zero"][name]["drop_BA"]
        for lvl in ("10", "30", "50"):
            assert round(e4[f"remove_0.{lvl[0]}"][name]["BA"], 4) == round(e2["curve_BA"][name]["zero"][lvl], 4)
