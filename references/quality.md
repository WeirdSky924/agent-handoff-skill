# Handoff Quality Guide

Use this reference when reviewing, repairing, compressing, or validating a repository handoff mechanism.

## Standard Maintenance Flow

1. Initialization: inspect repository structure, create or update handoff files, merge project-level handoff rules into Codex `AGENTS.md` and/or Claude Code `.claude/CLAUDE.md`, optionally create `AGENT_SESSION_PROMPTS.md`.
2. Session start, single layout: explicitly read `AGENT_HANDOFF.md`, determine the active subproject, then inspect only task-relevant source files.
3. Session start, multi layout: read `AGENT_HANDOFF.md`, `.agent-handoff/snapshot.md`, `.agent-handoff/risks.md`, and `.agent-handoff/backlog.md`; read other handoff files only when needed.
4. During work: update snapshot when objective/status changes, record decisions with reasons and evidence, record blockers and risks when they appear.
5. Closeout: update work log, validation history, next steps, risks, blockers, and stale state; then run the bundled maintenance script before final response.
6. Review/repair: remove contradictions, stale notes, chat transcript content, long logs, secrets, and unverifiable claims.

## Good `AGENT_HANDOFF.md`

- A new agent can understand the current objective and immediate next action within five minutes.
- All paths are locatable from the repository root.
- Current status, blockers, and backlog do not contradict each other.
- Important decisions include reasons and evidence.
- Validation history states what was run, whether it passed or failed, and any caveats.
- Unknowns are explicitly marked as `UNKNOWN`.
- The document reduces irrelevant reading, but does not replace source-code verification.
- The snapshot is replace-in-place current state and stays within 16 KiB / 240 lines when possible; it never silently grows past 32 KiB / 400 lines.
- Recent work log entries are still relevant; old details are compressed or archived.

## Good Multi-Document Handoff

- `AGENT_HANDOFF.md` is only an index, recovery route, and pointer file.
- `.agent-handoff/snapshot.md` is short and answers current objective, status, next action, active files, blockers, and open questions.
- `.agent-handoff/risks.md` contains all active blockers, risks, and unresolved `UNKNOWN` items.
- `.agent-handoff/backlog.md` contains actionable pending work without stale completed tasks.
- `.agent-handoff/validation.md` records passed, failed, and intentionally not-run checks.
- `.agent-handoff/decisions.md` contains durable decisions with reasons and evidence.
- `.agent-handoff/workspace.md` contains stable repository map and commands, not volatile task state.
- `.agent-handoff/archive.md` is not required for normal recovery.
- The required startup set is enough to recover what the previous agent was doing.
- Automatically rotated history is stored in `.agent-handoff/archive/` chunks no larger than 128 KiB and is not required for normal startup.

## Capacity And Rotation Contract

- Snapshot: soft limit `16 KiB` or `240` lines; hard limit `32 KiB` or `400` lines.
- Work log: rotate above `64 KiB` or `30` complete dated sections.
- Validation: rotate above `64 KiB` or `200` complete table rows.
- Backlog and risks: `32 KiB` each. Archive only mechanically identifiable completed backlog items; risks require semantic Agent review.
- Archive chunks: cap generated files at `128 KiB`.
- Single layout: warn above `32 KiB`; migrate to multi layout above the `64 KiB` hard limit.
- Before compacting a parseable snapshot, archive the original. If parsing fails, preserve the original and report an unresolved repair instead of guessing.

## Common Problems

- Writing a chat summary instead of task state.
- Recording vague outcomes like "optimized code" without file paths or validation.
- Starting a new task without refreshing the current objective.
- Capturing decisions without reason or evidence.
- Letting the file grow indefinitely with stale or contradictory notes.
- Appending a new snapshot below an old snapshot instead of replacing current-state fields.
- Pasting long command output, full code blocks, or failure logs.
- Writing guesses as facts.
- Forgetting to record tests that were not run.

## Repair Checklist

- Refresh `Handoff Snapshot` first.
- Verify active files from repository evidence.
- Replace stale objectives and stale next actions.
- Collapse old logs into concise summaries if they are no longer operationally useful.
- Preserve useful decisions and validation history.
- Mark unresolved questions as `UNKNOWN` instead of inventing answers.
- Confirm no secrets, credentials, tokens, or private logs were added.
- Run `python <skill-dir>/scripts/maintain_handoff.py --repo <repo-root> --compact-if-needed` and resolve every `UNRESOLVED` result.
- Re-read the final document before reporting completion.

## Multi-Document Recovery Test

A handoff passes recovery quality if a new agent can read only:

1. `AGENT_HANDOFF.md`
2. `.agent-handoff/snapshot.md`
3. `.agent-handoff/risks.md`
4. `.agent-handoff/backlog.md`
5. `.agent-handoff/validation.md`
6. `.agent-handoff/decisions.md` when decisions affect the task

And answer:

- What is the current objective?
- What is the current status?
- What is the next concrete action?
- Which files are active?
- What decisions constrain the work?
- What validation has passed, failed, or not run?
- What risks, blockers, or unknowns remain?
