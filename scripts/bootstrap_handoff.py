#!/usr/bin/env python3
"""Bootstrap repository-local Agent handoff files.

This script is intentionally conservative:
- It creates handoff files only when missing.
- It supports two layouts:
  - single: legacy single-file AGENT_HANDOFF.md
  - multi: AGENT_HANDOFF.md as an index plus .agent-handoff/*.md state files
- It creates or updates a marked handoff protocol block in AGENTS.md for Codex or DeepSeek Harness.
- It creates or updates a marked handoff protocol block in .claude/CLAUDE.md for Claude Code.
- It does not overwrite existing handoff state.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Iterable


START = "<!-- AGENT_HANDOFF_PROTOCOL:START -->"
END = "<!-- AGENT_HANDOFF_PROTOCOL:END -->"

READONLY_ALLOW = [
    "Read",
    "Grep",
    "Glob",
    "Bash(wc:*)",
    "Bash(sed -n:*)",
    "Bash(rg:*)",
    "Bash(grep:*)",
    "Bash(ls:*)",
    "Bash(pwd)",
    "Bash(git status:*)",
    "Bash(git diff:*)",
    "Bash(git log:*)",
    "Bash(git ls-files:*)",
]

HOOK_SCRIPT_START = "// AGENT_HANDOFF_HOOK:START"
HOOK_SCRIPT_END = "// AGENT_HANDOFF_HOOK:END"
HOOK_COMMAND = 'node "$CLAUDE_PROJECT_DIR/.claude/hooks/handoff-watch.mjs"'


def single_handoff_template(repo: Path) -> str:
    today = date.today().isoformat()
    root = str(repo)
    return f"""# Agent Handoff

> This file is the durable memory for agents working in this repository.
> A new agent should be able to read this file, inspect only the files needed for the current task, and continue without relying on previous chat history.

## Maintenance Contract

- Read this file before planning or editing.
- Update this file whenever task state, decisions, touched files, validation results, blockers, risks, or next actions change.
- Keep it factual and compact. Prefer file paths, commands, and concrete outcomes.
- Do not include secrets, credentials, long command logs, large code blocks, or chat transcript dumps.
- Replace stale notes instead of accumulating contradictory history.
- Mark uncertainty as `UNKNOWN` and resolve it from repository evidence when needed.

## Handoff Snapshot

- Last updated: {today}
- Last agent: Codex/Claude Code/DeepSeek Harness
- Workspace root: `{root}`
- Current objective: Establish durable Agent handoff mechanism for this repository.
- Current status: initialized
- Immediate next actions:
  - Inspect repository-specific files and replace `UNKNOWN` entries with verified facts.
- Active files:
  - `AGENT_HANDOFF.md`
  - `AGENTS.md`
  - `.claude/CLAUDE.md`
- Blockers: none
- Open questions:
  - Confirm whether handoff files should be committed or remain local-only.

## Workspace Map

- `.`: repository root.
- Main entry points:
  - `UNKNOWN`
- Test entry points:
  - `UNKNOWN`
- Docs/specs:
  - `UNKNOWN`

## Durable Project Context

- UNKNOWN: Populate with long-lived project facts verified from repository files or user input.

## Operating Rules For Future Agents

- Start each session by relying on preloaded project rules if present, then reading this file explicitly.
- Use this file as continuity memory, not as a replacement for reading source code.
- Verify behavior from source files before changing implementation.
- Keep edits scoped to the current task and existing project conventions.
- Do not modify generated dependency folders or unrelated files unless explicitly asked.
- Never revert unrelated user or agent changes.
- Before final response, update this file with status, changed files, validation, risks, and next steps.

## Decision Log

| Date | Decision | Reason | Evidence |
| --- | --- | --- | --- |
| {today} | Use `AGENT_HANDOFF.md` as repository-local durable agent memory. | Preserve continuity across sessions and agents. | User request or bootstrap action. |

## Current Work Log

### {today}

- Objective: Establish durable Agent handoff mechanism.
- Changed files:
  - `AGENT_HANDOFF.md`: Created initial durable handoff state.
  - `AGENTS.md`: Created or updated Codex/DeepSeek Harness project-level handoff rules if enabled.
  - `.claude/CLAUDE.md`: Created or updated Claude Code project-level handoff rules if enabled.
- Result: Initial handoff mechanism scaffolded.
- Remaining risks: Repository-specific context still contains `UNKNOWN` until source files are inspected.

## Task Backlog

- [ ] Replace `UNKNOWN` entries with verified repository facts.
- [ ] Confirm whether handoff files should be committed or gitignored.

## Validation History

| Date | Command/Check | Result | Notes |
| --- | --- | --- | --- |
| {today} | Bootstrap file creation | passed | Generated initial handoff scaffold; repository-specific facts still need review. |

## Handoff Update Template

Use this when ending a task or when the session may be interrupted:

```markdown
## Handoff Snapshot

- Last updated: YYYY-MM-DD
- Last agent: <agent/model/tool>
- Workspace root: `<repo root>`
- Current objective: <one sentence>
- Current status: <not started | in progress | blocked | implemented | validated>
- Immediate next actions:
  - <next concrete action>
- Active files:
  - `<path>`
- Blockers: <none or concrete blocker>
- Open questions:
  - <none or question>
```

Also update `Current Work Log`, `Decision Log`, `Validation History`, and `Task Backlog` when relevant.
"""


def multi_index_template(repo: Path) -> str:
    today = date.today().isoformat()
    root = str(repo)
    return f"""# Agent Handoff Index

> Entry point for durable agent handoff memory in this repository.
> Read this file first, then follow the Recovery Reading Order below.

## Maintenance Contract

- Keep this file short. It is an index and recovery route, not a work log.
- Store current task state in `.agent-handoff/snapshot.md`; replace stale fields instead of appending historical snapshots.
- Store durable facts, decisions, validation, backlog, risks, and archives in the dedicated files listed below.
- Keep all content factual and repository-based. Mark uncertainty as `UNKNOWN`.
- Do not include secrets, credentials, long logs, full code blocks, or chat transcript dumps.
- Before final response for any non-trivial task, update the relevant `.agent-handoff/` files.

## Handoff Layout

- `.agent-handoff/snapshot.md`: Current objective, status, next actions, active files, blockers, and open questions.
- `.agent-handoff/workspace.md`: Repository map, entry points, test commands, docs, and stable project context.
- `.agent-handoff/decisions.md`: Important decisions with reasons and evidence.
- `.agent-handoff/work-log.md`: Recent operational work log.
- `.agent-handoff/validation.md`: Validation commands/checks, results, and caveats.
- `.agent-handoff/backlog.md`: Pending work and follow-ups.
- `.agent-handoff/risks.md`: Risks, blockers, unknowns, and user/source confirmations needed.
- `.agent-handoff/archive.md`: Compressed old history that is not part of normal startup.
- `.agent-handoff/archive/`: Automatically rotated history chunks, each capped at 128 KiB.

## Size And Rotation Policy

- Snapshot soft limit: 16 KiB or 240 lines. Hard limit: 32 KiB or 400 lines.
- Work log limit: 64 KiB or 30 dated sections. Validation limit: 64 KiB or 200 table rows.
- Backlog and risks limit: 32 KiB each. Only completed backlog items may be archived mechanically; risks require Agent review.
- After updating handoff state, run the installed `agent-handoff/scripts/maintain_handoff.py --repo <repo> --compact-if-needed` when available.
- Maintenance must archive before replacing, preserve complete records, and leave unparseable or semantically unsafe content unchanged for Agent repair.

## Recovery Reading Order

1. Read this file.
2. Read `.agent-handoff/snapshot.md`.
3. Read `.agent-handoff/risks.md`.
4. Read `.agent-handoff/backlog.md`.
5. Read `.agent-handoff/validation.md` only if validation state matters for the current task.
6. Read `.agent-handoff/decisions.md` only when changing architecture, behavior, dependencies, or prior decisions.
7. Read `.agent-handoff/workspace.md` only when orientation, commands, entry points, or subproject boundaries are needed.
8. Read `.agent-handoff/work-log.md` only when recent implementation details are needed.
9. Read `.agent-handoff/archive.md` only when explicitly needed for old context.

## Current Pointer

- Last updated: {today}
- Workspace root: `{root}`
- Current state file: `.agent-handoff/snapshot.md`
- Primary next-action source: `.agent-handoff/snapshot.md`
- Risk source: `.agent-handoff/risks.md`
- Backlog source: `.agent-handoff/backlog.md`

## Project Rule Targets

- Codex / DeepSeek Harness project rules: `AGENTS.md`
- Claude Code project rules: `.claude/CLAUDE.md`

## Closeout Rule

For non-trivial work, update the relevant files before final response:

- Always update `.agent-handoff/snapshot.md`.
- Update `.agent-handoff/work-log.md` when files or task status changed.
- Update `.agent-handoff/validation.md` when checks were run or intentionally skipped.
- Update `.agent-handoff/decisions.md` when a durable decision was made.
- Update `.agent-handoff/backlog.md` and `.agent-handoff/risks.md` when follow-ups, blockers, risks, or unknowns changed.
- Run the handoff maintenance check and resolve hard-limit findings before final response.
"""


def multi_snapshot_template(repo: Path) -> str:
    today = date.today().isoformat()
    return f"""# Handoff Snapshot

## Current State

- Last updated: {today}
- Last agent: Codex/Claude Code/DeepSeek Harness
- Workspace root: `{repo}`
- Current objective: Establish durable multi-document Agent handoff mechanism for this repository.
- Current status: initialized
- Immediate next actions:
  - Inspect repository-specific files and replace `UNKNOWN` entries with verified facts.
- Active files:
  - `AGENT_HANDOFF.md`
  - `.agent-handoff/snapshot.md`
  - `AGENTS.md`
  - `.claude/CLAUDE.md`
- Blockers: none
- Open questions:
  - Confirm whether handoff files should be committed or remain local-only.

## Recovery Summary

- Use `AGENT_HANDOFF.md` as the index.
- Start here for the current objective and next action.
- Replace this current-state snapshot on update; do not append prior snapshots here.
- Do not treat this file as a replacement for source inspection.
"""


def multi_workspace_template() -> str:
    return """# Workspace Map

## Repository Structure

- `.`: repository root.
- `AGENT_HANDOFF.md`: handoff index and recovery route.
- `.agent-handoff/`: durable handoff state files.

## Main Entry Points

- `UNKNOWN`

## Test Entry Points

- `UNKNOWN`

## Docs And Specs

- `UNKNOWN`

## Durable Project Context

- UNKNOWN: Populate with long-lived facts verified from repository files or user input.

## Project Conventions

- UNKNOWN
"""


def multi_decisions_template() -> str:
    today = date.today().isoformat()
    return f"""# Decision Log

| Date | Decision | Reason | Evidence |
| --- | --- | --- | --- |
| {today} | Use multi-document Agent handoff memory. | Keep current state fast to read while preserving decisions, validation, backlog, and risks in dedicated files. | Bootstrap action. |

## Decision Guidelines

- Record durable decisions only.
- Include reason and evidence.
- Do not record guesses as decisions.
- If evidence is missing, mark it as `UNKNOWN`.
"""


def multi_work_log_template() -> str:
    today = date.today().isoformat()
    return f"""# Current Work Log

## {today}

- Objective: Establish durable multi-document Agent handoff mechanism.
- Changed files:
  - `AGENT_HANDOFF.md`: Created handoff index.
  - `.agent-handoff/`: Created structured handoff state files.
  - `AGENTS.md`: Created or updated Codex/DeepSeek Harness project-level handoff rules if enabled.
  - `.claude/CLAUDE.md`: Created or updated Claude Code project-level handoff rules if enabled.
- Result: Initial multi-document handoff mechanism scaffolded.
- Remaining risks: Repository-specific context still contains `UNKNOWN` until source files are inspected.

## Work Log Guidelines

- Keep only recent, still-operationally-useful work here.
- Move stale or long history to `archive.md` as a compressed summary.
- Prefer file paths and concrete outcomes over prose summaries.
"""


def multi_validation_template() -> str:
    today = date.today().isoformat()
    return f"""# Validation History

| Date | Command/Check | Result | Notes |
| --- | --- | --- | --- |
| {today} | Bootstrap file creation | passed | Generated initial multi-document handoff scaffold; repository-specific facts still need review. |

## Validation Guidelines

- Record commands/checks that were run.
- Record failed checks with concise cause and next action.
- Record checks that were intentionally not run as `not run`, with the reason.
- Do not paste long logs; summarize and reference files when needed.
"""


def multi_backlog_template() -> str:
    return """# Task Backlog

- [ ] Replace `UNKNOWN` entries with verified repository facts.
- [ ] Confirm whether handoff files should be committed or gitignored.

## Backlog Guidelines

- Keep tasks actionable.
- Remove completed or obsolete items.
- Link items to risks, decisions, or files when useful.
"""


def multi_risks_template() -> str:
    return """# Risks, Blockers, And Unknowns

## Current Blockers

- none

## Current Risks

- Repository-specific facts are still `UNKNOWN` until source files are inspected.

## Unknowns / Confirmations Needed

- UNKNOWN: Whether handoff files should be committed or remain local-only.

## Risk Guidelines

- Keep risks concrete.
- Mark uncertainty as `UNKNOWN`.
- Include the source needed to resolve each unknown when possible.
"""


def multi_archive_template() -> str:
    return """# Handoff Archive

This file stores compressed old history that should not be part of normal startup.

## Archive Guidelines

- Do not use this file for current state.
- Move stale but potentially useful history here as concise summaries.
- Keep pointers to relevant decisions, validation entries, or source files.
"""


def common_rule_body(layout: str) -> str:
    if layout == "multi":
        startup = """Before making a plan or editing files, read:

1. `AGENT_HANDOFF.md`
2. `.agent-handoff/snapshot.md`
3. `.agent-handoff/risks.md`
4. `.agent-handoff/backlog.md`
5. Additional `.agent-handoff/` files only when needed by the current task, following the Recovery Reading Order in `AGENT_HANDOFF.md`
6. The source files directly relevant to the user's current request

Use the handoff files as continuity memory, but verify implementation details from source files before changing behavior."""
        memory = """The repository uses multi-document durable handoff memory:

- `AGENT_HANDOFF.md`: index and recovery route
- `.agent-handoff/snapshot.md`: current objective, status, next actions, active files, blockers, and open questions
- `.agent-handoff/workspace.md`: repository map, entry points, commands, and stable context
- `.agent-handoff/decisions.md`: durable decisions with reasons and evidence
- `.agent-handoff/work-log.md`: recent operational work
- `.agent-handoff/validation.md`: validation commands/checks and results
- `.agent-handoff/backlog.md`: pending work
- `.agent-handoff/risks.md`: risks, blockers, unknowns, and confirmations
- `.agent-handoff/archive.md`: compressed old history

Maintain the smallest relevant file. Do not put all state into `AGENT_HANDOFF.md`; it is an index."""
        size = """- Keep `AGENT_HANDOFF.md` short; it is an index.
- Treat `.agent-handoff/snapshot.md` as replace-in-place current state, never an append-only history.
- Snapshot soft limit: 16 KiB or 240 lines. Hard limit: 32 KiB or 400 lines.
- Rotate `.agent-handoff/work-log.md` above 64 KiB or 30 dated sections.
- Rotate `.agent-handoff/validation.md` above 64 KiB or 200 table rows.
- Keep `.agent-handoff/backlog.md` and `.agent-handoff/risks.md` at or below 32 KiB. Only completed backlog items may be archived mechanically; risks need semantic review.
- Keep generated archive chunks at or below 128 KiB and keep archive history outside normal recovery.
- After updating handoff state, run the installed `agent-handoff/scripts/maintain_handoff.py --repo <repo> --compact-if-needed` when available. Archive before replacement and never rewrite unparseable state.
- In an ongoing uninterrupted chat, reread only relevant handoff files after compaction, resume, uncertainty, or task changes."""
        closeout = """Before any final response for a non-trivial task, update the relevant handoff files without waiting for the user to ask.

Minimum required updates:

- Refresh `.agent-handoff/snapshot.md` with current objective, status, next actions, active files, blockers, and open questions.
- Add or update `.agent-handoff/work-log.md` when files or task status changed.
- Add `.agent-handoff/validation.md` entries for commands/checks run or intentionally not run.
- Record durable decisions in `.agent-handoff/decisions.md`.
- Update `.agent-handoff/backlog.md` and `.agent-handoff/risks.md` when follow-ups, blockers, risks, or unknowns changed.
- Remove or rewrite stale state that would mislead the next agent.
- Run the bundled handoff maintenance script when available and resolve any hard-limit or unsafe-cleanup findings.

If the task was purely conversational and no project state changed, no file update is required."""
        checklist = "Before final response, update the relevant `.agent-handoff/` files with final task status, files changed, commands/checks run and outcomes, and remaining risks, blockers, open questions, or next steps."
    else:
        startup = """Before making a plan or editing files, read:

1. `AGENT_HANDOFF.md`
2. Any task-specific docs referenced by `AGENT_HANDOFF.md`
3. The source files directly relevant to the user's current request

Use `AGENT_HANDOFF.md` as continuity memory, but verify implementation details from source files before changing behavior."""
        memory = """`AGENT_HANDOFF.md` is the durable cross-session memory for this repository. Maintain it during every meaningful task.

Update it whenever any of these change:

- Current objective or status
- Active files
- Important decisions
- Files changed
- Validation commands and results
- Blockers, risks, open questions, or follow-up work

Keep updates concise and evidence-based. Do not paste secrets, credentials, long logs, large code blocks, or chat transcript dumps. Replace stale information instead of adding contradictory notes."""
        size = """- Keep `Handoff Snapshot` short, current, and action-oriented.
- Keep only recent, still-relevant work in `Current Work Log`.
- Prefer updating existing bullets over appending duplicate or contradictory notes.
- Treat 32 KiB as the single-document soft limit and 64 KiB as the hard limit. Migrate to multi-document layout instead of building complex in-file rotation above the hard limit.
- In an ongoing uninterrupted chat, reread only relevant sections after compaction, resume, uncertainty, or task changes."""
        closeout = """Before any final response for a non-trivial task, update `AGENT_HANDOFF.md` without waiting for the user to ask.

Minimum required updates:

- Refresh `Handoff Snapshot` with current objective, status, next actions, active files, and blockers.
- Add or update `Current Work Log` for the task.
- Add `Validation History` entries for commands or manual checks that were run.
- Record remaining risks, open questions, or follow-up work.
- Remove or rewrite stale state that would mislead the next agent.
- Check the single-document size and migrate to multi layout if it exceeds the hard limit.

If the task was purely conversational and no project state changed, no file update is required."""
        checklist = "Before final response, update `AGENT_HANDOFF.md` with final task status, files changed, commands/checks run and outcomes, and remaining risks, blockers, open questions, or next steps."

    return f"""## Required Startup Routine

{startup}

## Default Implementation Standard

For non-trivial development work, target production/commercial-grade quality by default rather than minimum viable implementation. Prefer robust, maintainable solutions with appropriate validation, runtime and edge-case consideration, and clear reporting of what was and was not tested. Keep scope aligned with the user's request; do not add unrelated features or speculative abstractions.

## Stable File Reading Protocol

To avoid Read tool line-number or offset drift:

1. Prefer dedicated search/read tools for ordinary file lookup, content search, and file reads.
2. Confirm file size before reading large or volatile files, using line counts or targeted searches when needed.
3. Search for exact targets first, then read small exact ranges around those targets.
4. Keep Read ranges no larger than 240 lines unless the file is known to be small.
5. If Read returns unexpected empty output, offset warnings, stale snippets, inconsistent line numbers, `file is shorter than the provided offset`, or an API termination after a Read attempt, stop paging with Read for that file immediately.
6. Treat Read `offset` as a line number, not a character offset. Never retry the same out-of-range offset, and never guess by adding zeros or using large approximate offsets. If the tool reports the file has N lines, all follow-up Read offsets for that file must be within `0..N`.
7. Recover from Read offset failure by re-anchoring with a targeted `Grep` for the section/title/symbol, or by reading a small known-valid range such as offset `0`; only then read a small range around the confirmed line number.
8. When Read becomes unreliable, use shell verification commands such as `wc -l`, `rg -n`, and `sed -n '<start>,<end>p'` with quoted paths; keep ranges small and record that fallback in validation notes when relevant.
9. Treat read-only shell inspection commands (`wc`, `rg`, `grep`, `sed -n`, `ls`, `pwd`, and non-mutating `git status`/`git diff`/`git log`/`git ls-files`) as safe query operations. They should be pre-approved in project settings where possible so source verification does not require repeated manual approval.
10. Do not propose or edit code based on uncertain offsets; re-anchor with search results first.

## Continuation Recovery Guard

If the user says `continue`, `继续`, `Continue from where you left off.`, or any equivalent continuation request, treat it as an explicit instruction to resume the task. Do not answer `No response requested.` and do not stop silently. First state the last known objective and next concrete action, then continue. If context is insufficient, recover from the handoff files and task-relevant source files before acting.

## Durable Handoff Memory

{memory}

## Handoff Size Discipline

{size}

## Mandatory Closeout Protocol

{closeout}

## Work Discipline

- Do not assume which subproject is active. Infer it from the user request, handoff files, and repository evidence.
- Prefer existing project conventions over new abstractions.
- Read files before editing them.
- Keep edits scoped to the task.
- Do not modify generated dependency folders unless explicitly asked.
- Never revert unrelated user or agent changes.
- Record validation honestly. If tests or checks were not run, say so in handoff files and in the final response.

## Session Closeout Checklist

{checklist}"""


def rule_block(layout: str) -> str:
    layout_label = "multi-document" if layout == "multi" else "single-document"
    return f"""{START}
# Agent Handoff Protocol

Layout: {layout_label}

{common_rule_body(layout)}
{END}
"""


def session_prompts(layout: str) -> str:
    if layout == "multi":
        return """# Agent Session Prompts

## New Window Startup

```text
Confirm project rules are loaded, then read AGENT_HANDOFF.md and follow its Recovery Reading Order. At minimum read .agent-handoff/snapshot.md, .agent-handoff/risks.md, and .agent-handoff/backlog.md before planning.

Recover the current objective, status, immediate next action, active files, blockers, validation caveats, and source files that need inspection. Read only task-relevant files after that. During the task, update the smallest relevant .agent-handoff file whenever objective, decisions, changed files, validation, risks, blockers, or next steps change. Complete handoff closeout before the final response.
```

## Continue Specific Task

```text
Continue this task: <specific task>.

Treat this as an explicit request to continue execution. Do not answer "No response requested." First state what you believe the previous step was, identify the next concrete action, then continue. If context is insufficient, recover from AGENT_HANDOFF.md and the required .agent-handoff files before acting.

Start by reading AGENT_HANDOFF.md, then .agent-handoff/snapshot.md, .agent-handoff/risks.md, and .agent-handoff/backlog.md. Inspect task-relevant source files. Maintain the multi-document handoff: update snapshot at the start, decisions when durable choices are made, work-log when files change, validation when checks run or are skipped, and risks/backlog when follow-ups or unknowns change.
```

## Closeout

```text
Before ending this turn, update the multi-document handoff: replace the current state in .agent-handoff/snapshot.md, update .agent-handoff/work-log.md, record .agent-handoff/validation.md, update .agent-handoff/backlog.md and .agent-handoff/risks.md, and remove or rewrite stale state. Run the installed agent-handoff maintenance script with --repo <repo> --compact-if-needed when available; resolve hard-limit findings without discarding unparseable or semantically unsafe state. Then report what changed, what was validated, and what remains.
```

## Handoff Quality Review

```text
Review and directly repair the multi-document handoff so a new agent can take over. Check that AGENT_HANDOFF.md is only an index, snapshot is replace-in-place current state within 16 KiB / 240 lines when possible and never above 32 KiB / 400 lines, next actions are concrete, paths are locatable, decisions have reasons and evidence, validation is recorded, and stale, contradictory, speculative, or chat-transcript content is archived or removed safely. Run the bundled maintenance check when available.
```
"""
    return """# Agent Session Prompts

## New Window Startup

```text
Confirm project rules are loaded, then explicitly read AGENT_HANDOFF.md. Treat it as durable project state, not as chat history.

Recover the current objective, status, immediate next action, active files, blockers, and source files that need inspection. Read only task-relevant files after that. During the task, update AGENT_HANDOFF.md whenever objective, decisions, changed files, validation, risks, blockers, or next steps change. Complete handoff closeout before the final response.
```

## Continue Specific Task

```text
Continue this task: <specific task>.

Treat this as an explicit request to continue execution. Do not answer "No response requested." First state what you believe the previous step was, identify the next concrete action, then continue. If context is insufficient, recover from AGENT_HANDOFF.md before acting.

Start by confirming project rules are loaded and reading AGENT_HANDOFF.md, then inspect task-relevant source files. Maintain AGENT_HANDOFF.md during the task: update objective and active files at the start, record decisions with reasons, record changed files, record validation commands and results, and update final status, risks, blockers, and next steps before closing.
```

## Closeout

```text
Before ending this turn, update AGENT_HANDOFF.md: refresh Handoff Snapshot, update Current Work Log, record Validation History, update Task Backlog, and remove or rewrite stale state. Then report what changed, what was validated, and what remains.
```

## Handoff Quality Review

```text
Review and directly repair AGENT_HANDOFF.md so a new agent can take over. Check that the objective is current, next actions are concrete, paths are locatable, decisions have reasons and evidence, validation is recorded, and stale, contradictory, speculative, or chat-transcript content is removed.
```
"""


def skill_template_text(relative_path: str) -> str:
    path = Path(__file__).resolve().parent.parent / relative_path
    if not path.exists():
        raise SystemExit(f"Missing skill template: {path}")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def hook_script_template() -> str:
    return skill_template_text("templates/handoff-watch.mjs")


def hook_settings_template() -> dict:
    data = json.loads(skill_template_text("templates/claude-settings-hooks.json"))
    if not isinstance(data, dict) or not isinstance(data.get("hooks"), dict):
        raise SystemExit("Invalid hook settings template: templates/claude-settings-hooks.json")
    return data


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_text(path: Path, content: str, dry_run: bool, changed: list[str]) -> None:
    old = read_text(path)
    if old == content:
        return
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    item = str(path)
    if item not in changed:
        changed.append(item)


def create_if_missing(path: Path, content: str, dry_run: bool, changed: list[str], notes: list[str]) -> None:
    if path.exists():
        notes.append(f"Preserved existing {path}; inspect and repair manually if needed.")
        return
    write_text(path, content, dry_run, changed)


def replace_marked_block(original: str, block: str) -> str:
    start = original.find(START)
    end = original.find(END)
    if start != -1 and end != -1 and end > start:
        end += len(END)
        prefix = original[:start].rstrip()
        suffix = original[end:].lstrip()
        parts = [part for part in [prefix, block.strip(), suffix] if part]
        return "\n\n".join(parts) + "\n"
    if not original.strip():
        return block.strip() + "\n"
    return original.rstrip() + "\n\n" + block.strip() + "\n"


def replace_marked_script(original: str, block: str) -> str:
    start = original.find(HOOK_SCRIPT_START)
    end = original.find(HOOK_SCRIPT_END)
    if start != -1 and end != -1 and end > start:
        end += len(HOOK_SCRIPT_END)
        prefix = original[:start].rstrip()
        replacement = block.strip()
        suffix = original[end:].lstrip()

        if replacement.startswith("#!") and prefix:
            if prefix.startswith("#!") and len(prefix.splitlines()) == 1:
                prefix = ""
            else:
                replacement = "\n".join(replacement.splitlines()[1:])

        parts = [part for part in [prefix, replacement, suffix] if part]
        return "\n".join(parts) + "\n"
    return original


def add_gitignore_entries(repo: Path, entries: Iterable[str], dry_run: bool, changed: list[str]) -> None:
    path = repo / ".gitignore"
    lines = read_text(path).splitlines()
    existing = {line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")}
    missing = [entry for entry in entries if entry not in existing]
    if not missing:
        return
    additions = ["", "# Agent handoff local memory", *missing]
    content = "\n".join(lines + additions).lstrip("\n").rstrip() + "\n"
    write_text(path, content, dry_run, changed)


def merge_readonly_permissions(repo: Path, dry_run: bool, changed: list[str]) -> None:
    path = repo / ".claude" / "settings.json"
    if path.exists():
        try:
            data = json.loads(read_text(path))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Cannot merge permissions into invalid JSON: {path}: {exc}") from exc
    else:
        data = {}

    permissions = data.setdefault("permissions", {})
    allow = permissions.setdefault("allow", [])
    if not isinstance(allow, list):
        raise SystemExit(f"Cannot merge permissions: permissions.allow is not a list in {path}")

    for item in READONLY_ALLOW:
        if item not in allow:
            allow.append(item)

    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    write_text(path, content, dry_run, changed)


def load_settings_json(path: Path) -> dict:
    if path.exists():
        try:
            data = json.loads(read_text(path))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Cannot update invalid JSON: {path}: {exc}") from exc
    else:
        data = {}
    if not isinstance(data, dict):
        raise SystemExit(f"Cannot update settings: root JSON value is not an object in {path}")
    return data


def merge_hook_settings(repo: Path, dry_run: bool, changed: list[str]) -> None:
    path = repo / ".claude" / "settings.json"
    data = load_settings_json(path)
    template = hook_settings_template()

    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"Cannot merge hooks: hooks is not an object in {path}")

    for event, groups in template["hooks"].items():
        existing_groups = hooks.setdefault(event, [])
        if not isinstance(existing_groups, list):
            raise SystemExit(f"Cannot merge hooks: hooks.{event} is not a list in {path}")

        found = False
        for group in existing_groups:
            if not isinstance(group, dict):
                continue
            commands = group.get("hooks", [])
            if not isinstance(commands, list):
                continue
            for command in commands:
                if isinstance(command, dict) and command.get("type") == "command" and command.get("command") == HOOK_COMMAND:
                    found = True
                    break
            if found:
                break

        if not found:
            existing_groups.extend(groups)

    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    write_text(path, content, dry_run, changed)


def install_hooks(repo: Path, dry_run: bool, changed: list[str], notes: list[str]) -> None:
    script_path = repo / ".claude" / "hooks" / "handoff-watch.mjs"
    script = hook_script_template()
    script_ready = True
    if script_path.exists():
        existing = read_text(script_path)
        if existing == script:
            pass
        elif HOOK_SCRIPT_START in existing and HOOK_SCRIPT_END in existing:
            write_text(script_path, replace_marked_script(existing, script), dry_run, changed)
        else:
            notes.append(f"Preserved existing {script_path}; it has no Agent handoff markers, so hook script was not overwritten.")
            notes.append("Skipped hook settings merge to avoid wiring an unverified existing hook script.")
            script_ready = False
    else:
        write_text(script_path, script, dry_run, changed)

    if script_ready:
        merge_hook_settings(repo, dry_run, changed)


def create_single_layout(repo: Path, dry_run: bool, changed: list[str], notes: list[str]) -> None:
    create_if_missing(repo / "AGENT_HANDOFF.md", single_handoff_template(repo), dry_run, changed, notes)


def create_multi_layout(repo: Path, dry_run: bool, changed: list[str], notes: list[str]) -> None:
    handoff_dir = repo / ".agent-handoff"
    create_if_missing(repo / "AGENT_HANDOFF.md", multi_index_template(repo), dry_run, changed, notes)
    create_if_missing(handoff_dir / "snapshot.md", multi_snapshot_template(repo), dry_run, changed, notes)
    create_if_missing(handoff_dir / "workspace.md", multi_workspace_template(), dry_run, changed, notes)
    create_if_missing(handoff_dir / "decisions.md", multi_decisions_template(), dry_run, changed, notes)
    create_if_missing(handoff_dir / "work-log.md", multi_work_log_template(), dry_run, changed, notes)
    create_if_missing(handoff_dir / "validation.md", multi_validation_template(), dry_run, changed, notes)
    create_if_missing(handoff_dir / "backlog.md", multi_backlog_template(), dry_run, changed, notes)
    create_if_missing(handoff_dir / "risks.md", multi_risks_template(), dry_run, changed, notes)
    create_if_missing(handoff_dir / "archive.md", multi_archive_template(), dry_run, changed, notes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap Agent handoff files for a repository.")
    parser.add_argument("--repo", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument(
        "--platform",
        choices=["codex", "claude", "dsh", "both"],
        default="both",
        help=(
            "Project rule target: codex and dsh update AGENTS.md, claude updates "
            ".claude/CLAUDE.md, both updates both files and covers all three hosts."
        ),
    )
    parser.add_argument(
        "--layout",
        choices=["single", "multi"],
        default="multi",
        help="Handoff layout: single creates legacy AGENT_HANDOFF.md, multi creates AGENT_HANDOFF.md plus .agent-handoff/*.md.",
    )
    parser.add_argument("--session-prompts", action="store_true", help="Create AGENT_SESSION_PROMPTS.md if missing.")
    parser.add_argument("--gitignore", action="store_true", help="Add local handoff files to .gitignore if missing.")
    parser.add_argument("--allow-readonly", action="store_true", help="Claude Code only: merge safe read-only query permissions into .claude/settings.json.")
    parser.add_argument("--install-hooks", action="store_true", help="Claude Code only: install advisory handoff hooks into .claude/hooks and merge .claude/settings.json.")
    parser.add_argument(
        "--skip-codex-rules",
        action="store_true",
        help="Do not create or update the shared Codex/DSH AGENTS.md rules.",
    )
    parser.add_argument("--skip-claude-rules", action="store_true", help="Do not create or update .claude/CLAUDE.md.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing files.")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not repo.exists() or not repo.is_dir():
        raise SystemExit(f"Repository path is not a directory: {repo}")

    changed: list[str] = []
    notes: list[str] = []

    if args.layout == "multi":
        create_multi_layout(repo, args.dry_run, changed, notes)
    else:
        create_single_layout(repo, args.dry_run, changed, notes)

    write_agents = args.platform in ("codex", "dsh", "both") and not args.skip_codex_rules
    write_claude = args.platform in ("claude", "both") and not args.skip_claude_rules

    if write_agents:
        agents_path = repo / "AGENTS.md"
        updated = replace_marked_block(read_text(agents_path), rule_block(args.layout))
        write_text(agents_path, updated, args.dry_run, changed)

    if write_claude:
        claude_path = repo / ".claude" / "CLAUDE.md"
        updated = replace_marked_block(read_text(claude_path), rule_block(args.layout))
        write_text(claude_path, updated, args.dry_run, changed)

    if args.session_prompts:
        prompts = repo / "AGENT_SESSION_PROMPTS.md"
        create_if_missing(prompts, session_prompts(args.layout), args.dry_run, changed, notes)

    if args.gitignore:
        entries = ["AGENT_HANDOFF.md", "AGENT_SESSION_PROMPTS.md"]
        if args.layout == "multi":
            entries.append(".agent-handoff/")
        add_gitignore_entries(repo, entries, args.dry_run, changed)

    if args.allow_readonly:
        merge_readonly_permissions(repo, args.dry_run, changed)

    if args.install_hooks:
        install_hooks(repo, args.dry_run, changed, notes)

    mode = "DRY RUN" if args.dry_run else "UPDATED"
    print(f"{mode}: {repo}")
    print(f"Layout: {args.layout}")
    print(f"Platform rules: {args.platform}")
    if changed:
        print("Changed files:")
        for item in changed:
            print(f"- {item}")
    else:
        print("Changed files: none")
    if notes:
        print("Notes:")
        for note in notes:
            print(f"- {note}")
    print("Next: inspect generated files and replace UNKNOWN placeholders with repository facts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
