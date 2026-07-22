# Codex Handoff Rules

Merge a marked block into project-level `AGENTS.md` for Codex. If the repository already has an `AGENTS.md`, preserve existing guidance and replace only the marked block when present. Do not edit user-level `~/.codex/AGENTS.md` unless the user explicitly asks.

Codex uses `AGENTS.md` as repository instructions. This file is the Codex-side counterpart to Claude Code's `.claude/CLAUDE.md`.

Prefer generating the block with `scripts/bootstrap_handoff.py` so it matches the chosen layout:

```bash
python <skill-dir>/scripts/bootstrap_handoff.py --repo <repo-root> --platform codex --layout multi
python <skill-dir>/scripts/bootstrap_handoff.py --repo <repo-root> --platform codex --layout single
```

If the markers already exist, replace only the marked block.

## Markers

```markdown
<!-- AGENT_HANDOFF_PROTOCOL:START -->
...
<!-- AGENT_HANDOFF_PROTOCOL:END -->
```

## Multi-Document Startup Rule

For `--layout multi`, the generated Codex rule instructs future agents to read:

1. `AGENT_HANDOFF.md`
2. `.agent-handoff/snapshot.md`
3. `.agent-handoff/risks.md`
4. `.agent-handoff/backlog.md`
5. Additional `.agent-handoff/` files only when needed
6. Task-relevant source files

`AGENT_HANDOFF.md` must remain an index. Current task state belongs in `.agent-handoff/snapshot.md` and replaces stale state rather than appending historical snapshots.

## Capacity Rule

Generated Codex rules use the shared maintenance policy: snapshot soft limit `16 KiB / 240 lines`, hard limit `32 KiB / 400 lines`; work log `64 KiB / 30` dated sections; validation `64 KiB / 200` rows; backlog and risks `32 KiB`; archive chunks `128 KiB`. After handoff updates, run the installed skill's `scripts/maintain_handoff.py --repo <repo> --compact-if-needed` when available. Preserve unparseable state for manual repair.

## Continuation Recovery Guard

If the user says `continue`, `继续`, `Continue from where you left off.`, or any equivalent continuation request, treat it as an explicit instruction to resume the task. Do not answer `No response requested.` and do not stop silently. First state the last known objective and next concrete action, then continue. If context is insufficient, recover from the handoff files and task-relevant source files before acting.

## Stable File Reading Protocol

Generated Codex rules include a defensive Read protocol:

- Keep Read ranges no larger than 240 lines unless the file is known to be small.
- Treat Read `offset` as a line number, not a character offset.
- Stop paging with Read for a file after unexpected empty output, offset warnings, stale snippets, inconsistent line numbers, `file is shorter than the provided offset`, or API termination after a Read attempt.
- Re-anchor with targeted search before any follow-up read after an offset failure.
- Use small, quoted, read-only shell inspections such as `wc -l`, `rg -n`, and `sed -n '<start>,<end>p'` when Read becomes unreliable.
- Do not propose or edit code based on uncertain offsets.

## Single-Document Startup Rule

For `--layout single`, the generated Codex rule instructs future agents to read:

1. `AGENT_HANDOFF.md`
2. Task-specific docs referenced by `AGENT_HANDOFF.md`
3. Task-relevant source files

All state stays in `AGENT_HANDOFF.md`.

## Closeout Requirement

For non-trivial tasks:

- Multi layout: update the smallest relevant `.agent-handoff/` files and run the maintenance check before final response.
- Single layout: update `AGENT_HANDOFF.md` before final response.

Do not paste secrets, credentials, long logs, full code blocks, or chat transcript dumps.
