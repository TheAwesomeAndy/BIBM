# AGENTS.md

Instructions for any AI coding or research agent working in this repository,
whatever tool it runs in. Claude-specific rules are in `CLAUDE.md`; where the
two overlap, `CLAUDE.md` is the stricter and more detailed text and it governs.

## What this repository is

The code, aggregate results, and manuscript for an **accepted** paper:

> A. Lane, W. Tang, and B. Nelson, "On the Edge of Stability: Spiking Reservoir
> State-Space Encoding of Affective EEG," 2026 IEEE International Conference on
> Bioinformatics and Biomedicine (BIBM), Dallas, TX, 2026.

The camera-ready version has been submitted. The paper studies one component of
ARSPI-Net, its temporal encoding stage: a fixed LIF reservoir with BSC6
spike-bin encoding, evaluated as a measurement operator under perturbation.

**The accepted paper is a baseline to preserve. It is not a draft to improve.**

## Read first, in this order

1. This file.
2. `CLAUDE.md`: scope, protocol, data, and wording rules.
3. `docs/BASELINE.md`: what is frozen and how to check it.
4. `python3 scripts/memory.py digest`: recent decisions and lessons.
5. `docs/ARCHITECTURE.md`: what each directory does and who owns it.
6. For scientific work: `docs/RESEARCH_MAP.md` and `docs/EXPERIMENT_REGISTRY.md`.
7. Before running anything: `docs/REPRODUCIBILITY.md` and `docs/HARNESS_OVERRIDES.md`.
8. Before handing off or working in parallel: `docs/AGENT_HANDOFF.md`.

## Hard rules

1. **Do not change accepted results.** Nothing in `outputs/aggregate/` is
   edited or regenerated in place. Never alter an output to make a check pass.
2. **Do not revise the accepted manuscript.** The verification tools exist to
   detect drift. Their findings are not instructions to rewrite the paper.
3. **Do not change scientific behavior silently.** This covers the reservoir
   equations, BSC6 encoding, PCA fitting, validation splits, seeds, feature
   extraction, perturbations, bootstrapping, and metrics. A refactor of
   `analysis/` needs characterization tests first and equivalence shown after.
   If equivalence cannot be shown, keep the original and report the limit.
4. **Keep the validation protocol.** `StratifiedGroupKFold`, 5 folds, seeds
   42 to 46, subjects as groups, train-only standardization, balanced L2
   logistic readout. Leave-one-subject-out is a separate experiment that needs
   the author's approval (`docs/HARNESS_OVERRIDES.md`, item 1).
5. **Never commit restricted data** or anything that identifies it: no
   pickles, arrays, raw EEG, subject-level files, private links, or local
   restricted paths. See `CLAUDE.md`, Data isolation.
6. **Work in phases.** State the verification criteria before changing files.
   Finish the approved phase, report, and stop for approval.
7. **Do not commit, push, tag, delete research artifacts, or rewrite history
   without the author's explicit authorization.**
8. **No tool attribution** in commits, pull requests, documents, or comments.
9. **Stay in scope.** The out-of-scope list is in `CLAUDE.md`. Lineage from
   ARSPI-Net does not bring the rest of ARSPI-Net into this repository.

## Say what kind of fact you are stating

Label statements as **verified** (observed in this session), **historical**
(recorded earlier, not re-run), **new** (produced after acceptance), or
**open** (not known). Definitions and examples are in `docs/AGENT_HANDOFF.md`.
Quote numbers from files, never from recall. Report failures and limits
plainly.

## Ownership at a glance

| Paths | Owner | You may |
|---|---|---|
| `analysis/`, `docs/`, `AGENTS.md`, `CLAUDE.md`, `README.md` | project | change, under the rules above |
| `outputs/aggregate/`, `manuscript/` | project, frozen | read |
| `scripts/`, `papercheck/`, `tools/`, `makefiles/`, `playbooks/`, `.claude/`, `harness/policies/`, `harness/task_specs/` | imported harness | read; record deviations in `docs/HARNESS_OVERRIDES.md` |
| `harness/memory/memory.jsonl` | project | append through `scripts/memory.py` only |

## Commands that work today

```sh
python3 scripts/memory.py digest                          # load project memory
sha256sum -c --quiet docs/baseline/results.sha256         # accepted artifacts intact
python3 analysis/check_author_wording.py                  # manuscript wording gate
python3 -m papercheck manuscript/main_bibm2026.tex        # known failure, see overrides item 3
python3 scripts/check_table_manifest.py harness/table_manifest.yaml   # known failure, item 2
```

Running an experiment needs restricted data and overwrites accepted outputs.
Read `docs/REPRODUCIBILITY.md`, procedure E, first.

## Known traps

- `analysis/experiment2_rawsignal.py` is a superseded experiment and a live
  library. Four experiments import it.
- The two subject-bootstrap functions use different seeds. They are not
  interchangeable.
- Harness tools default to `manuscript/main.tex`, which does not exist. Pass
  `manuscript/main_bibm2026.tex`.
- There is no test suite yet. "Tests pass" is not a claim available at the
  baseline.
- No dependency file exists yet. Recorded versions are in
  `docs/REPRODUCIBILITY.md`.
- Session storage in cloud environments is temporary. Uncommitted work,
  including new journal entries, is lost when the session ends. Ask for
  authorization to commit before the session closes.

## Future work

New experiments and journal-extension methods follow the convention in
`docs/EXPERIMENT_REGISTRY.md` (separate IDs, separate output directory,
provenance block, verification status). They never overwrite or blend into the
accepted baseline.
