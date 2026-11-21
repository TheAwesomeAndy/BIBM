"""Every table cell in the accepted manuscript against the aggregate outputs.

Read-only: these tests compare; they never write the manuscript, the outputs,
or the table manifest. They replace reliance on the harness manifest gate for
Table II, whose generated rows follow an earlier table layout
(docs/HARNESS_OVERRIDES.md, item 2).
"""
from __future__ import annotations

import re

import pytest

import export_paper_values as EX

CHANCE = 1.0 / 3.0


def _table(tex: str, label: str) -> list[list[str]]:
    body = tex.split(f"\\label{{{label}}}", 1)[1].split("\\end{tabular}", 1)[0]
    body = body.split("\\midrule", 1)[1].split("\\bottomrule", 1)[0]
    rows = [r.strip() for r in body.split("\\\\") if r.strip()]
    return [[c.strip() for c in r.split("&")] for r in rows]


def _num(cell: str) -> float:
    return float(re.search(r"[-+]?\d+\.\d+|[-+]?\d+", cell.replace("$", "")).group())


def _pct(cell: str) -> int:
    return int(re.search(r"(\d+)\\%", cell).group(1))


def test_table1_fixed_encoder_rows_verbatim(manuscript_tex):
    for _name, row, _vals in EX.table_clean()["tab:clean"]:
        assert row in manuscript_tex


def test_table1_eegnet_row(manuscript_tex, aggregate):
    row = next(r for r in _table(manuscript_tex, "tab:clean") if r[0] == "D0")
    e = aggregate("e3_eegnet_signal.json")["BA"]["remove_0.0"]["EEGNet"]
    shown = [float(x) for x in re.findall(r"\d\.\d{3}", row[2])]
    assert shown == [round(e["BA"], 3), round(e["ci95"][0], 3), round(e["ci95"][1], 3)]


def test_table3_rows_verbatim(manuscript_tex):
    rows = EX.table_rawsignal()["tab:rawsignal"]
    assert len(rows) == 6
    for _name, row, _vals in rows:
        assert row in manuscript_tex


def test_table2_all_cells(manuscript_tex, aggregate):
    """Table II in the accepted layout: rows are encoders; Clean, Zero, Mean, two retention columns."""
    e2 = aggregate("e2_trainonly_pca_fills.json")
    e3 = aggregate("e3_eegnet_signal.json")["BA"]
    rows = {re.sub(r"\\quad|\\,|\s", "", r[0]): r for r in _table(manuscript_tex, "tab:dropconf")}
    assert set(rows) == {"EEGNet", "+aug.", "ERP-window", "Band-power", "Reservoir"}

    for name in ("ERP-window", "Band-power", "Reservoir"):
        clean = e2["clean_BA"][name]["point"]
        zero = e2["dropout_30"]["zero"][name]["drop_BA"]
        mean = e2["dropout_30"]["mean"][name]["drop_BA"]
        r = rows[name]
        assert [_num(r[1]), _num(r[2]), _num(r[3])] == [round(clean, 3), round(zero, 3), round(mean, 3)]
        assert _pct(r[4]) == round(100 * zero / clean)                              # raw retention
        assert _pct(r[5]) == round(100 * (mean - CHANCE) / (clean - CHANCE))        # above-chance retention

    for label, model in (("EEGNet", "EEGNet"), ("+aug.", "EEGNet+aug")):
        clean = e3["remove_0.0"][model]["BA"]
        rem = e3["remove_0.3"][model]["BA"]                                         # signal-level removal
        r = rows[label]
        assert [_num(r[1]), _num(r[2])] == [round(clean, 3), round(rem, 3)]
        assert r[3] == "--"
        assert _pct(r[4]) == round(100 * rem / clean)
        assert _pct(r[5]) == round(100 * (rem - CHANCE) / (clean - CHANCE))


def test_paper_values_csv_matches_outputs(root):
    """paper_values.csv is what the exporter would write from the committed JSON."""
    import csv

    with open(root / "outputs" / "aggregate" / "paper_values.csv", newline="") as fh:
        stored = {(r["table"], r["row"], r["column"]): r["value"] for r in csv.DictReader(fh)}
    fresh = {(tab, row, col): f"{v:.6f}" for tab, rows in EX.tables().items()
             for row, _tex, vals in rows for col, v in vals.items()}
    assert stored == fresh


@pytest.mark.parametrize("fig", ["fig_reservoir_dyn.pdf", "fig_erp.pdf", "fig_impute_subj.pdf", "fig_deap_aug.pdf"])
def test_manuscript_figures_present(root, manuscript_tex, fig):
    assert f"{{{fig}}}" in manuscript_tex
    assert (root / "manuscript" / "figures" / "imported" / fig).is_file()
