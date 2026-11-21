# Accepted baseline (BIBM 2026, paper S60204)

This file defines what "the accepted baseline" means in this repository and how
to prove it has not moved.

## Status

- Paper: A. Lane, W. Tang, and B. Nelson, "On the Edge of Stability: Spiking
  Reservoir State-Space Encoding of Affective EEG," 2026 IEEE International
  Conference on Bioinformatics and Biomedicine (BIBM), Dallas, TX, 2026.
- Accepted (Doctoral Forum, S60204). The camera-ready version has been submitted.
- Baseline commit: `1667277e43b51e3cc2b88d2ef99ef265c8441dbc` (merge of PR #41).
- Lineage: the paper isolates the temporal encoding stage of ARSPI-Net (LISAT
  2023 and 2024 papers, cited in the manuscript as `lane2023arspi` and
  `lane2024arspi`). Lineage is provenance. It does not widen the scope rules in
  `CLAUDE.md`.

The tag `bibm2026-camera-ready` marks the baseline commit. It was created
locally on 2026-11-21 with the author's approval. Check `git ls-remote --tags
origin` before relying on it: at the time of writing it had not been pushed.

## What is frozen

| Class | Files | Rule |
|---|---|---|
| Accepted results | `outputs/aggregate/*` | Never edited, never regenerated in place |
| Accepted manuscript | `manuscript/main_bibm2026.tex`, the two PDFs, `manuscript/cover_note.md` | Not revised. The verification tools check it; they are not a reason to rewrite it |
| Accepted figures | the four files named in `CLAUDE.md`, Figure policy | Not regenerated |
| Accepted implementation | `analysis/*.py` at the baseline commit | Changed only by an approved, behavior-preserving refactor with equivalence tests |

## Checksums

Two SHA-256 manifests were written at the baseline commit:

- `docs/baseline/results.sha256`: aggregate outputs, manuscript source and
  PDFs, cover note, and the four manuscript figures. **These must always
  verify.** A failure means an accepted artifact changed.
- `docs/baseline/implementation.sha256`: every `analysis/*.py` file. This one is
  a reference point. It is expected to stop verifying when an approved refactor
  lands; at that point the refactor's equivalence evidence replaces it, and the
  file is regenerated in the same commit with a note in the memory journal.

Verify from the repository root:

```sh
sha256sum -c --quiet docs/baseline/results.sha256
sha256sum -c --quiet docs/baseline/implementation.sha256
```

## Numerical anchors

The anchors that tie the code to the accepted numbers are in
`docs/CODE_AUDIT.md`, section 3. The primary one is the pooled-PCA reservoir
clean balanced accuracy, per-fold mean 0.4626, printed by
`analysis/regen_reservoir_embedding.py`. Reproducing any anchor needs the
restricted data (see `docs/REPRODUCIBILITY.md`).

## Rules for work after the baseline

1. New experiments do not write into `outputs/aggregate/`. They follow the
   extension convention in `docs/EXPERIMENT_REGISTRY.md`.
2. A newer result never replaces an accepted one. If a later run disagrees with
   the paper, record both and open a `question` entry in the memory journal.
3. Methods developed for the journal extension stay out of the scripts that
   produced the accepted numbers.
4. Known open items inherited from the camera-ready (for example the
   corrected-window rerun, `docs/CODE_AUDIT.md` A18, and the membrane histogram,
   memory entry #38) are extension work, not baseline fixes.
