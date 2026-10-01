# BIBM 2026 Conference Paper 1

This repository contains the IEEE BIBM 2026 conference-paper carve-out from the operational-distinctness work.

## Working title

**On the Edge of Stability: Spiking-Reservoir State-Space Encoding of Affective EEG**

## Submission target

IEEE International Conference on Bioinformatics and Biomedicine (BIBM) 2026. The intended route is the BIBM 2026 Doctoral Forum submission portal, with the manuscript written and formatted as a standard IEEE conference proceedings paper.

## Scope

This paper isolates the reservoir temporal-encoding component. It focuses on affective ERP observations, fixed LIF reservoir encoding, six-bin spike-count encoding, PCA-compressed reservoir embeddings, subject-level validation, and perturbation characterization.

## Reserved for later journal work

The repository should not contain the full integrated ARSPI-Net manuscript, graph-topological tPLV analysis, structure-function coupling, closed-loop EFE results, or broad diagnostic claims.

## Current manuscript files

- `manuscript/main_bibm2026.tex` — active IEEE two-column manuscript (single entry point).
- `manuscript/main_bibm2026.pdf` — compiled output (IEEEtran, 6 pages).
- `manuscript/IEEEtran.cls` — vendored IEEEtran V1.8b class (compile from `manuscript/`).
- `manuscript/figures/imported/` — finished figure assets imported from the source repository.
- `manuscript/overlap_log.md` — publication-overlap and journal-preservation log.
- `manuscript/cover_note.md` — optional submission note.
- `manuscript/cv_appendix_template.tex` — one-page CV appendix template required by the call.

The TikZ figure sources under `manuscript/figures/*.tex` are retained only as backups;
the active manuscript uses the imported finished figures.

## Building

```
cd manuscript
latexmk -pdf -interaction=nonstopmode main_bibm2026.tex
```

## Imported figures

| Manuscript figure | Imported asset | Source path in original repo |
|---|---|---|
| Fig. 1 (motivation) | `fig_overview_evidence_streams.pdf` | `figures/taffc/` |
| Fig. 2 (reservoir objects) | `fig_reservoir_dynamics.pdf` | `figures/tcds_hardening/` |
| Fig. 3 (perturbation response) | `ana03_robustness_degradation_curves.pdf` | `figures/tcds_ready9/analysis/` |
| (backup, unused) | `arch_fig_pipeline_overview.pdf` | `manuscript/figures/architecture/` |
