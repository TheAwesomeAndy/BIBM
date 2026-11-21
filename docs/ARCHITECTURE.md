# Architecture

What each part of the repository does, who owns it, and how the parts depend on
each other. This describes the tree at the accepted baseline
(`docs/BASELINE.md`). It is a map, not a redesign.

## Two code bases in one repository

| Owner | Paths | Change policy |
|---|---|---|
| **Project** (this paper) | `analysis/`, `outputs/aggregate/`, `manuscript/`, `docs/`, `CLAUDE.md`, `AGENTS.md`, `README.md`, `CITATION.cff` | Governed by `docs/BASELINE.md` |
| **Imported harness** | `scripts/`, `papercheck/`, `tools/`, `makefiles/`, `playbooks/`, `.claude/`, `harness/policies/`, `harness/task_specs/`, example files in `harness/` | Synced from `TheAwesomeAndy/myResearchAssitantHarness`. Do not edit locally. Project deviations go in `docs/HARNESS_OVERRIDES.md` |
| **Project state inside the harness tree** | `harness/memory/memory.jsonl`, `harness/papercheck.toml`, `harness/table_manifest.yaml` (generated), `scripts/verify_latex.py` (local bug fix) | Project-owned; listed as deliberate differences in `README.md` |

## Data flow

```
restricted inputs (outside the repo)
  SHAPE feature pickle: X_ds (N,256,34), y, subjects      DEAP s01..s32.dat
        |                                                       |
        v                                                       v
  analysis/experiment_*.py, regen_*, reanalysis_*        analysis/deap_replication.py
        |                                                       |
        +--------------------> outputs/aggregate/*.json <-------+
                                     |
              +----------------------+-----------------------+
              v                                              v
  analysis/make_fig_*.py                          analysis/export_paper_values.py
  -> manuscript/figures/imported/*.pdf            -> outputs/aggregate/paper_values.csv
                                                  -> harness/table_manifest.yaml
              |                                              |
              +------------> manuscript/main_bibm2026.tex <--+ (checked, not written)
```

Only aggregate, de-identified values cross from the restricted inputs into the
repository.

## Project code: `analysis/`

There is no package. Each file is a script; shared code is imported from
sibling scripts through `sys.path.insert(0, <analysis dir>)`.

### Modules that other scripts depend on

| Module | Provides | Imported by |
|---|---|---|
| `perturbations.py` | `removal_draw`, `remove_channels`, `amplitude_noise`, `temporal_jitter`, `SIGNAL_CONDITIONS`; all draws keyed to `(seed, fold)` | E3, E4 |
| `reanalysis_subject_bootstrap.py` (alias `RB`) | `_resolve_pickle`, `drop_channels`, `fill_test`, `run_oof`, `subject_bootstrap` (seed 12345), `paired_diff_ci` (seed 999), `ERP_WINDOWS_MS`, `FILLS`, `DROP_LEVELS`, `N_BOOT` | E1, E2, E3, E4, E5, Fig. 1, Fig. 2 |
| `experiment2_rawsignal.py` (alias `E2S`) | `bandpower_all`, `erp_all`, `_fit_pred` | E1/E2, E3, E4, E5 |
| `experiment_camera_ready.py` (alias `EC`) | `weights(rho)`, `bsc6(X, rho)`, `damage`, `fit_pred`, `fold_embeddings`, constants | E4, E5, Fig. 1 |

**Trap.** `experiment2_rawsignal.py` is superseded as an *experiment* (its JSON
output is not used by the paper) but it is a live *library*: four experiments
import its band-power and ERP-window functions. Do not delete or "clean up" it.

### Known duplication (not yet consolidated)

| Component | Locations | Equivalence status |
|---|---|---|
| LIF reservoir update loop | `regen_reservoir_embedding.regen`, `experiment2_rawsignal.bsc6_all`, `experiment_camera_ready.bsc6`, `experiment_camera_ready.damage` | The three encoders are bitwise equal on the synthetic fixture (`tests/test_reservoir.py`). `damage` shares the update but is tested only against pinned values |
| Weight initialization | `regen_reservoir_embedding.init_weights`, `experiment2_rawsignal.init_weights`, `experiment_camera_ready.weights` | Bitwise equal at rho 0.9 (tested). `weights(rho)` divides by the spectral radius without the zero guard |
| ERP-window means | `RB.build_blocks`, `E2S.erp_all`, inline in `EC.run_e2` | First two equal (tested); the inline copy is the same by reading |
| Readout fit | `EC.fit_pred`, `E2S._fit_pred`, inline in `RB.run_oof` and `regen.validate`, `deap_replication.fit_pred` | First three give equal probabilities (tested); the last two are the same settings by reading, with different return conventions |
| Subject bootstrap | `RB.subject_bootstrap` (seed 12345), `E2S.subj_boot` (seed 7) | **Not interchangeable.** Different RNG seeds give different intervals (a test pins the difference) |
| PCA embedding of training codes | `fit_transform` in `regen` and `E2S`; `fit` then `transform` elsewhere | **Not interchangeable.** See `docs/CODE_AUDIT.md` A10 |
| Constants (`SEEDS`, reservoir parameters, windows, `N_BOOT`) | up to six files | Same values by reading |

Consolidation is Phase 4 work. The characterization tests now exist. Rows
marked "not interchangeable" must stay separate.

### Execution assumptions an agent must know

- Data paths come from environment variables with three different fallback
  mechanisms (`docs/REPRODUCIBILITY.md`).
- `regen_reservoir_embedding.py` writes a subject-level `.npy` outside the
  repository (default under the system temp directory); the pooled-PCA
  sensitivity script reads it back.
- Importing `experiment_eegnet_signal.py` calls `torch.set_num_threads(2)`.
  E3 determinism was observed with that setting (`docs/CODE_AUDIT.md`, section 3).
- `experiment_controls.py` recovers the fold index as `i % 5` from a flat fold
  list; the order of that list is load-bearing.
- `export_paper_values.py` overwrites `outputs/aggregate/paper_values.csv` and
  `harness/table_manifest.yaml`.

## Verification layer

| Tool | Owner | Checks |
|---|---|---|
| `analysis/check_author_wording.py` | project | Author wording rules (memory entry #16) |
| `scripts/check_table_manifest.py` + `harness/table_manifest.yaml` | harness + project | Table cells in the manuscript against `paper_values.csv` |
| `python -m papercheck` | harness | Manuscript structure and language rules |
| `scripts/verify_latex.py` | harness, locally fixed | LaTeX build |
| `scripts/check_forbidden_phrases.py`, `tools/check_path_markers.py` | harness | Phrase and path hygiene |
| `docs/baseline/*.sha256` | project | Accepted artifacts unchanged |
| `tests/` (`make test`) | project | Baseline integrity, reservoir, perturbations, features, fills, protocol, bootstrap, and every cell of Tables I to III |

Current gate status, including two gates that fail for known reasons, is in
`docs/HARNESS_OVERRIDES.md`.

## Knowledge layer

| Source | Holds | Authority |
|---|---|---|
| `harness/memory/memory.jsonl` | Decisions, lessons, open questions, in time order | The single record of *why*. Other docs link to entries by `#id` and do not restate them |
| `docs/CODE_AUDIT.md` | Camera-ready audit findings A1 to A21 and reproduction anchors | Historical record, dated 2026-10-01 |
| `analysis/README.md` | Paper element to script to output map, run order | Authoritative for the accepted paper |
| `docs/EXPERIMENT_REGISTRY.md` | Per-experiment parameters, outputs, status | Index over the above, plus extension rules |
| `docs/RESEARCH_MAP.md` | Scientific concept to code to evidence | Index |

## Tests and environment (added after the baseline)

| Path | Role |
|---|---|
| `pyproject.toml` | Pinned dependencies and pytest configuration. The code is still scripts, not a package |
| `tests/` | Project test suite. Synthetic signals only; reads no restricted data and writes nothing into `outputs/` |
| `tests/golden/synthetic_reservoir.json` | Pinned reservoir outputs of the baseline implementation on the synthetic fixture |
| `Makefile` | `make check` runs checksums, the wording gate, and the tests. Includes the harness makefile with this project's manuscript path |
| `.github/workflows/tests.yml` | Runs `make check` on push and pull request |

The harness's own unit tests and fixtures live in the upstream harness
repository and are not installed here. There is still no Python package.
