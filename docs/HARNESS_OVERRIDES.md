# Harness overrides

The research harness in this repository is imported from
`TheAwesomeAndy/myResearchAssitantHarness` and kept byte-identical to it so
that it can be re-synced (`README.md`, Harness provenance). It is generic. This
project is specific. Where the two disagree, **this file and `CLAUDE.md` win**,
and the harness file is left unedited.

Decision recorded in the memory journal (tags `harness`, `overrides`).

## Precedence

1. Explicit instruction from the author in the current session.
2. `CLAUDE.md` (project rules) and `docs/BASELINE.md`.
3. This file.
4. Harness policies, playbooks, skills, and commands.

## Overrides

### 1. Validation protocol: grouped k-fold, not leave-one-subject-out

- Harness text: `harness/policies/rigor_policy.md` says to use
  leave-one-subject-out for human-subject data.
- Project rule: `StratifiedGroupKFold`, 5 folds, seeds 42 to 46, subjects as
  groups. This is the accepted paper's protocol (`CLAUDE.md`, Validation
  protocol).
- Reconciliation: the policy's purpose is that no subject spans folds. The
  accepted protocol satisfies that. The enforcing check,
  `papercheck/checks/methods.py` (`methods.leakage`), already accepts grouped
  validation, so only the policy prose conflicts.
- Leave-one-subject-out remains a separate experiment that needs explicit
  approval. If approved, it is an extension experiment
  (`docs/EXPERIMENT_REGISTRY.md`), not a change to the baseline.

### 2. Table-value gate fails on Table II (known, numbers are correct)

- Observed 2026-11-21: `python3 scripts/check_table_manifest.py
  harness/table_manifest.yaml` reports 16 failures, all `tab:dropconf`, all
  "required text not found".
- Cause: the camera-ready returned Table II to the accepted layout (rows are
  encoders, columns are Clean, Zero, Mean, and two retention columns; memory
  entry #36). `analysis/export_paper_values.py` still generates rows for the
  earlier layout (rows are fill rules).
- The values the manifest expects (0.417, 0.536, 0.487, 0.472, 0.578) appear
  in the manuscript table. The EEGNet rows and the retention percentages have
  no gate coverage.
- Do not edit the manuscript to satisfy the gate.
- Resolution (Phase 3): the exporter and its two generated files are part of
  the frozen baseline, so they were left as they are. The project test
  `tests/test_manuscript_tables.py` checks every cell of Tables I to III
  against the aggregate JSON in the accepted layout, including the EEGNet rows
  and both retention columns. Use `make test`, not the manifest gate, as the
  table check. The manifest gate keeps failing on Table II by design.

### 3. `papercheck` limits aligned with the accepted paper

- Observed 2026-11-21: `python3 -m papercheck manuscript/main_bibm2026.tex`
  reports one error, `abstract.length` (267 words against a limit of 200),
  and six warnings.
- The 200-word limit is a harness default. The BIBM call sets no abstract
  limit (memory entry #5). The accepted abstract stands.
- `docs/CODE_AUDIT.md`, section 4, records this gate as PASS on 2026-10-01.
  That statement is historical and does not describe the current result.
- Resolution (Phase 3): `harness/papercheck.toml`, which is project-owned,
  now allows 300 words, 8 sentences, and 7 keywords. Result on 2026-11-21:
  PASS with 0 errors and 4 warnings (`ethics.statement`, `intro.gap`,
  `limits.pivot`, `related.position`). The warnings describe the accepted
  paper and are not acted on.
- `human_subjects` stays `false`. Setting it to `true` would turn the ethics
  warning into a gate against a clause the author removed on purpose in the
  camera-ready. Author decision.

### 4. Main manuscript path

- Harness default: `manuscript/main.tex`, in both makefiles,
  `scripts/phase_gate.py`, and the skill, command, and playbook text.
- Project file: `manuscript/main_bibm2026.tex`.
- With the default, `make -f makefiles/ManuscriptHarness.mk harness-verify`
  skips the LaTeX, citation, table-scan, and papercheck steps without failing.
- Resolution (Phase 3): the root `Makefile` includes the harness makefile
  with `MAIN_TEX` set, so `make harness-verify` and the other `harness-*`
  targets use the right file. Calling the harness makefile directly with `-f`
  still needs the path:

  ```sh
  make harness-paper
  make -f makefiles/ManuscriptHarness.mk harness-verify MAIN_TEX=manuscript/main_bibm2026.tex
  python3 scripts/paper_check.py manuscript/main_bibm2026.tex --profile draft
  ```

  `make harness-verify` as a whole still stops at the phrase gate (item 6).

  When a skill or command says `manuscript/main.tex`, read it as
  `manuscript/main_bibm2026.tex`. `python3 -m papercheck` with no path already
  uses the right file through `harness/papercheck.toml`.

### 5. Harness self-tests are not installed here

- `make ... harness-tests` and `/verify` call `python -m unittest discover -s
  tests`. There is no `tests/` directory. Zero tests run.
- `python3 scripts/run_fixture_tests.py` expects a `fixtures/` directory that
  is not installed. It reports failures, and its passing cases are not
  evidence of anything in this repository.
- The figures "140/140 unit tests" and "70/70 fixtures" in
  `docs/CODE_AUDIT.md` describe the upstream harness repository.
- The project's own tests are in `tests/` and run with `make test` (pytest).
  They are unrelated to the harness self-tests. `harness-tests` uses unittest
  discovery and finds none of them.

### 6. Phrase and path gates report known false positives

- `scripts/check_forbidden_phrases.py` flags `CLAUDE.md` and
  `manuscript/overlap_log.md` for containing words that those files list as
  banned, and flags long-dash characters in `README.md`, `CLAUDE.md`, and
  `analysis/README.md`.
- `tools/check_path_markers.py` flags the local data directory name in
  `CLAUDE.md`, `analysis/README.md`, and `analysis/deap_replication.py`. The
  harness's own privacy policy recommends that directory name.
- Neither finding indicates restricted data in the repository. A new finding
  outside the files listed here is real and must be resolved.
- The manuscript wording gate for this project is
  `analysis/check_author_wording.py`, not the repo-wide phrase gate
  (memory entries #16, #26).

### 7. Harness skills written for drafting and submission

The skills `wall-drafting`, `idea-gate`, `journal-selection`, `cover-letter`,
`reviewer-response`, and `latex-revision`, and the matching commands, assume a
manuscript in progress. For the accepted BIBM paper they do not apply: the
manuscript is frozen (`docs/BASELINE.md`). They remain available for a future
journal extension, which would have its own manuscript file. `memory-keeper`
and `manuscript-audit` (read-only) apply as written, subject to item 4.

### 8. Attribution

Project rule (`CLAUDE.md`): no tool attribution, footer text, session links,
or "generated by" language in commits, pull requests, manuscripts, or
comments. This overrides any default of the agent tooling in use.

## Re-syncing the harness

Follow `README.md`. After a re-sync, confirm this file still describes the
conflicts accurately, and re-apply the project-local differences listed there.
