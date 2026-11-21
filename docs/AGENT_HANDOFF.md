# Agent handoff and collaboration

How agents (and people) pass work to each other in this repository without
losing context or corrupting the accepted baseline.

## Where knowledge goes

There is one durable record: the memory journal,
`harness/memory/memory.jsonl`, written through `scripts/memory.py`.

| Kind of knowledge | Where it goes |
|---|---|
| A decision and its reason | journal, kind `decision` |
| Something a gate or a person caught | journal, kind `lesson` |
| An unresolved scientific or engineering question | journal, kind `question` |
| State of a task in progress, for the next agent | handoff note (below), then summarized in the journal |
| Stable facts about structure | `docs/ARCHITECTURE.md`, `docs/RESEARCH_MAP.md`, `docs/EXPERIMENT_REGISTRY.md` |

Do not start a second log, notes file, or status document. If the docs and the
journal disagree, the newer journal entry is the lead to follow: verify it
against the code, then fix the doc.

Journal privacy rules are in `harness/policies/memory_policy.md`. Peer-review
content stays out of git (memory entry #27).

## Session start

```sh
python3 scripts/memory.py digest
sha256sum -c --quiet docs/baseline/results.sha256
git status --short
```

Then read `AGENTS.md`. A failing checksum or a dirty tree at the start of a
session is the first thing to report.

## Evidence classes

Every statement in a handoff, a report, or a journal entry belongs to one of
four classes. Label it.

| Label | Meaning | Example |
|---|---|---|
| **verified** | Observed in this session, with the command or file | "ran the checksum check; it passed" |
| **historical** | Recorded earlier by someone else; not re-run now | "the audit reproduced 0.4626 on 2026-10-01" |
| **new** | Produced after acceptance; not part of the accepted paper | an extension experiment's result |
| **open** | Not known | "torch version for E3 is not recorded" |

Never promote historical to verified by restating it. Never report a number
from memory; quote the file it came from.

## Handoff note

Give this to the next agent in the final message of a session, and record a
one-entry summary in the journal. Keep it short.

```
HANDOFF
Task:            <one sentence>
Phase and gate:  <phase name; what approval is pending, from whom>
Branch / commit: <branch>, <short SHA or "uncommitted">
Done (verified): <items, each with the command or file that shows it>
Not done:        <items>
Changed files:   <list, or "none">
Baseline:        <results.sha256 passes | fails: which file>
Gates run:       <gate: result>, ...
Assumptions:     <anything relied on but not verified>
Open questions:  <for the author or the next agent>
Do not touch:    <anything the next agent might be tempted to change>
Next step:       <the single next action>
```

Journal summary:

```sh
python3 scripts/memory.py add decision "<what was decided or completed, why, and what is pending>" --tags handoff,<topic>
```

## Working in parallel

### Ownership

- One agent owns one task. A task names the paths it may change.
- Two agents never change the same file at the same time. If a task needs a
  file another task owns, stop and ask the coordinator.
- These files have a single writer at any time: `harness/memory/memory.jsonl`,
  `docs/EXPERIMENT_REGISTRY.md`, `docs/BASELINE.md`, `CLAUDE.md`, `AGENTS.md`.
  Parallel agents send journal entries to the coordinator in their handoff
  note; the coordinator appends them. This avoids duplicate entry IDs.

### Isolation

- Each parallel task works on its own branch or git worktree.
- Branch names state the task, for example `tests/reservoir-characterization`.
- Restricted data is never copied into a worktree. Scripts reach it through
  environment variables only.
- Reproduction runs happen in a worktree, never in the main tree, because the
  experiment scripts overwrite `outputs/aggregate/`.

### Change tracking

- One logical change per commit. A refactor and a behavior change never share
  a commit.
- Commit messages state what changed and how it was verified. No tool
  attribution (`CLAUDE.md`).
- A commit that touches `analysis/` states the equivalence evidence, or states
  that behavior changed and who approved it.
- Before any commit: run the restricted-data check (`git status`, confirm no
  ignored data type is staged) and the baseline checksum check.

### Conflict resolution

1. Files under the frozen classes in `docs/BASELINE.md`: the baseline version
   wins. Neither side's change is kept without author approval.
2. `harness/memory/memory.jsonl`: keep every entry from both sides, in
   timestamp order; renumber duplicate IDs on the later branch and fix any
   `#id` references that branch added.
3. Imported harness files: the upstream version wins. Move the local intent to
   `docs/HARNESS_OVERRIDES.md`.
4. Everything else: the owner of the task that touched the file first decides.
   If the two changes encode different scientific choices, stop and ask the
   author. Do not merge two analyses into a hybrid.

### Review

An agent does not approve its own change to `analysis/`. A second agent, given
the diff and the tests but not the first agent's conclusion, checks it. The
author approves anything that alters a number.

## Stop conditions

Stop and ask the author when:

- a baseline checksum fails;
- a reproduction disagrees with an accepted number;
- a task would change a protocol element listed in `CLAUDE.md`;
- restricted data, or a path or identifier that points at it, is about to be
  committed;
- two instructions conflict and `docs/HARNESS_OVERRIDES.md` does not cover it.
