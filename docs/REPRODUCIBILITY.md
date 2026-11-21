# Reproducibility

What is known to run, in which environment, and what is not yet verified. This
file separates recorded facts from gaps on purpose.

## Environment

### Recorded for the accepted results

From `docs/CODE_AUDIT.md`, section 3 (2026-10-01):

| Package | Version | Source of the record |
|---|---|---|
| numpy | 2.4.6 | audit |
| scikit-learn | 1.9.1 | audit |
| Python | not recorded | |
| scipy | not recorded | |
| torch (E3) | not recorded | |
| matplotlib, pymupdf, Pillow (figures) | not recorded | |

The author does not have the unrecorded versions. They cannot be recovered
from this repository.

### Constraints visible in the code

- numpy 2.0 or later: `experiment2_rawsignal.bandpower_all` calls `np.trapezoid`.
- scikit-learn with `StratifiedGroupKFold` (1.0 or later).
- E3 ran on CPU with two torch threads; the audit reports identical reruns
  under that setting.

### Not yet provided

There is no dependency file and no lock file at the baseline. Adding one is
Phase 3 of the modernization plan. Until then, treat any environment other
than the recorded one as unverified: PCA with the randomized solver, the
logistic solver, and torch training can all shift low-order digits between
library versions.

## Data

Nothing restricted is in the repository, by rule (`CLAUDE.md`, Data isolation).

| Input | Contents | How scripts find it |
|---|---|---|
| SHAPE feature pickle | `X_ds` (N, 256, 34), `y`, `subjects`; also `conv_feats` and a zeroed `lsm_bsc6_pca` | environment variable `ARSPI_SHAPE_FEATURES` |
| DEAP `data_preprocessed_python` | `s01.dat` to `s32.dat` | environment variable `DEAP_DIR` |
| Regenerated pooled-PCA embedding | subject-level `.npy`, written by `regen_reservoir_embedding.py` | environment variable `ARSPI_RESERVOIR_NPY` |

**Always set the environment variables explicitly.** The fallbacks differ by
script: `reanalysis_subject_bootstrap._resolve_pickle` searches for a sibling
`operational-distinctness-paper/data/` directory, while
`regen_reservoir_embedding.py` and `experiment2_rawsignal.py` use a fixed
default path, and the `.npy` default is under the system temp directory. Point
`ARSPI_RESERVOIR_NPY` at the local restricted-data directory named in
`CLAUDE.md`, not at a shared temp location.

Access: SHAPE is access-controlled (Laboratory for Clinical Affective
Neuroscience, Stony Brook University). DEAP is available from its authors
under the DEAP licence.

## Procedures

### A. Check that the accepted artifacts are intact (no data needed)

```sh
sha256sum -c --quiet docs/baseline/results.sha256
python3 analysis/check_author_wording.py
```

Verified on 2026-11-21 at the baseline commit: both pass.

### B. Check the manuscript against the aggregate outputs (no data needed)

```sh
python3 scripts/check_table_manifest.py harness/table_manifest.yaml
```

**Fails at the baseline** for Table II, for a known reason unrelated to the
numbers. See `docs/HARNESS_OVERRIDES.md`, item 2.

### C. Build the paper (needs a LaTeX installation)

```sh
cd manuscript && latexmk -pdf -interaction=nonstopmode main_bibm2026.tex
```

Acceptance checks are listed in `CLAUDE.md`, Build validation. Not verified in
the session that wrote this file: no LaTeX installation was available.

### D. Reproduce the numerical anchor (needs SHAPE)

```sh
export ARSPI_SHAPE_FEATURES=<path to the pickle>
export ARSPI_RESERVOIR_NPY=<path in the local restricted-data directory>
python3 analysis/regen_reservoir_embedding.py
```

Expected: `regenerated reservoir clean BA = 0.4626` and `MATCH`. The script's
own tolerance is 0.02 around 0.463; the audit reproduced 0.4626 exactly with
the recorded versions.

### E. Reproduce the accepted experiments (needs SHAPE and DEAP)

Follow the run order in `analysis/README.md`. **Do not run it inside this
working tree unless the goal is a deliberate reproduction**: every script
overwrites its file in `outputs/aggregate/`. To reproduce safely:

1. Work in a separate clone or worktree.
2. Run the scripts.
3. Compare the new JSON with the committed JSON value by value.
4. Report differences. Do not commit regenerated outputs over the accepted ones.

Cross-script consistency checks that should hold after a faithful rerun are in
`docs/CODE_AUDIT.md`, section 3, and memory entry #29.

## Verification status

| Claim | Status | By whom |
|---|---|---|
| Accepted artifacts match their checksums | verified 2026-11-21 | this modernization, Phase 2 |
| Anchor 0.4626 reproduces | historical, 2026-10-01 | camera-ready audit |
| E2, E3 reruns identical to first runs | historical, 2026-10-01 | camera-ready audit |
| Paper builds, body ends on page 6 | historical | memory entries #36, #41 |
| Results reproduce on library versions other than the recorded ones | **unverified** | |
| Any experiment run since acceptance | **none** | |
| Reproduction by anyone outside the author's environment | **none recorded** | |

## Known limits

- Real-data reproduction cannot be done in a cloud session unless the
  restricted data is made reachable from that session by the author.
- The four reservoir implementations have not been compared by an automated
  test.
- Output JSON files carry a protocol string but no commit, version, or
  timestamp. Their provenance is the git history and `docs/CODE_AUDIT.md`.
