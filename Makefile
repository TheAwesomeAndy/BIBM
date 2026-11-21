# Project entry points. The imported harness makefiles are included unchanged;
# the variables below point them at this project's manuscript
# (docs/HARNESS_OVERRIDES.md, item 4).

PYTHON ?= python3
MAIN_TEX := manuscript/main_bibm2026.tex
CSV_DIR := outputs/aggregate

include makefiles/ManuscriptHarness.mk

.PHONY: check test test-fast baseline wording

# Everything that needs neither restricted data nor LaTeX.
check: baseline wording test

baseline:
	sha256sum -c --quiet docs/baseline/results.sha256
	sha256sum -c --quiet docs/baseline/implementation.sha256

wording:
	$(PYTHON) analysis/check_author_wording.py

test:
	$(PYTHON) -m pytest

# Skips the comparison against the baseline commit (two subprocess runs).
test-fast:
	$(PYTHON) -m pytest --deselect tests/test_refactor_equivalence.py
