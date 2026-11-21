"""The working tree computes exactly what the accepted baseline computed.

The baseline analysis/ code is checked out from the baseline commit into a
temporary directory and run in a separate process on the synthetic fixture.
The working tree is run the same way. Every output must be bitwise equal.

Scope and limit: this covers the functions exercised by
tests/equivalence_driver.py on synthetic signals. It does not show equivalence
on the restricted EEG data, and it does not cover EEGNet (E3) or DEAP, whose
scripts are left unmodified.
"""
from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

BASELINE_COMMIT = "1667277e43b51e3cc2b88d2ef99ef265c8441dbc"


def _run(driver, analysis_dir, out):
    res = subprocess.run([sys.executable, str(driver), str(analysis_dir), str(out)],
                         capture_output=True, text=True)
    assert res.returncode == 0, res.stderr[-2000:]
    return dict(np.load(out, allow_pickle=False))


@pytest.fixture(scope="module")
def results(root, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("equivalence")
    base = tmp / "baseline_analysis"
    base.mkdir()
    ls = subprocess.run(["git", "ls-tree", "--name-only", f"{BASELINE_COMMIT}:analysis"],
                        cwd=root, capture_output=True, text=True)
    if ls.returncode != 0:
        pytest.skip("baseline commit not available in this checkout (shallow clone?)")
    for name in ls.stdout.split():
        name = name.rsplit("/", 1)[-1]
        if name.endswith(".py"):
            blob = subprocess.run(["git", "show", f"{BASELINE_COMMIT}:analysis/{name}"],
                                  cwd=root, capture_output=True, check=True)
            (base / name).write_bytes(blob.stdout)
    driver = root / "tests" / "equivalence_driver.py"
    return _run(driver, base, tmp / "baseline.npz"), _run(driver, root / "analysis", tmp / "current.npz")


def test_same_outputs_exist(results):
    baseline, current = results
    assert sorted(baseline) == sorted(current)
    assert len(baseline) > 100


def test_outputs_bitwise_equal(results):
    baseline, current = results
    different = [k for k in sorted(baseline)
                 if baseline[k].dtype != current[k].dtype
                 or baseline[k].shape != current[k].shape
                 or not np.array_equal(baseline[k], current[k], equal_nan=True)]
    assert different == []
