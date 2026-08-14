# Optional Claude Code Hook Enforcement

Use hooks only when the user asks for stronger operational reminders than written project rules. Hooks must check and remind; they must not generate handoff content, because closeout state needs repository context and agent judgment.

This hook guidance is Claude Code specific. Codex and DSH do not use Claude hook configuration, and the default bootstrap command does not install hooks unless `--install-hooks` is passed.

## Safety Contract

- Keep hooks lightweight, local, and project-scoped.
- Always emit valid JSON when output is needed.
- Always exit with status code `0`, including error paths.
- Always return `continue: true` when returning JSON.
- Never return `decision: "block"`, `continue: false`, or `decision: "approve"`.
- Never use hook failures to terminate, block, or close an agent session.
- Never write handoff files from a hook.
- Never invoke `maintain_handoff.py`, Python, or any other mutating maintenance command from a hook.
- Never call the network, install dependencies, delete files, start services, or mutate project state.
- Preserve existing user hook scripts unless they contain the Agent handoff hook markers.

`statusMessage` belongs to `.claude/settings.json` and is only a Claude Code UI label while a hook command runs. The hook script must not depend on it. Event behavior must come from Claude Code hook stdin JSON, especially `hook_event_name`.

## Recommended Install

Use the bootstrap script only when the user explicitly asks for hooks:

```bash
python <skill-dir>/scripts/bootstrap_handoff.py --repo <repo-root> --install-hooks
```

This command:

- Creates `.claude/hooks/handoff-watch.mjs` if missing.
- Replaces only the marked Agent handoff hook block if the target script already contains the hook markers.
- Preserves an existing `.claude/hooks/handoff-watch.mjs` with no Agent handoff markers.
- Merges missing hook entries into `.claude/settings.json`.
- Avoids duplicating hook commands on repeated runs.

Use `--dry-run` first when changing an existing project:

```bash
python <skill-dir>/scripts/bootstrap_handoff.py --repo <repo-root> --install-hooks --dry-run
```

## Template Files

- `templates/claude-settings-hooks.json`: Event-aware `.claude/settings.json` hook snippet for manual merge or script installation.
- `templates/handoff-watch.mjs`: Complete advisory hook script that checks handoff file freshness and structure.

When manually installing hooks, merge only the `hooks` object from `templates/claude-settings-hooks.json` into the project's `.claude/settings.json`. Do not overwrite unrelated settings.

## Installed Target Files

```text
.claude/
  settings.json
  hooks/
    handoff-watch.mjs
```

## Supported Events

| Event | Behavior |
| --- | --- |
| `SessionStart` | Inject handoff health and recovery reading guidance as additional context. |
| `UserPromptSubmit` | Inject context only when the prompt suggests handoff, continue, resume, compact, closeout, or recovery work, or when handoff structure is missing. |
| `PreCompact` | Remind the agent to update handoff files before compaction if task state changed. |
| `Stop` | Remind the agent to update relevant handoff files before final response if repository state changed. |
| `SubagentStop` | Same closeout reminder behavior as `Stop`, with stop-loop suppression. |
| `SessionEnd` | Emit a quiet session-end summary. |

## Checks

General checks:

- `AGENT_HANDOFF.md` exists.
- `AGENT_HANDOFF.md` is not older than the configured threshold.
- Claude Code hook stdin JSON can be parsed.

Multi-document layout checks:

- `.agent-handoff/` exists.
- Expected files exist: `snapshot.md`, `workspace.md`, `decisions.md`, `work-log.md`, `validation.md`, `backlog.md`, `risks.md`, `archive.md`.
- `AGENT_HANDOFF.md` contains `## Recovery Reading Order`.
- `AGENT_HANDOFF.md` contains `## Handoff Layout`.
- `.agent-handoff/snapshot.md` contains `## Current State` when the snapshot file is present.
- Snapshot capacity is reported at the `16 KiB / 240 line` soft limit and `32 KiB / 400 line` hard limit.
- Work log (`64 KiB / 30` sections), validation (`64 KiB / 200` rows), backlog (`32 KiB`), and risks (`32 KiB`) overages produce advisory warnings.

Single-document layout checks:

- `AGENT_HANDOFF.md` contains `## Handoff Snapshot`.
- `AGENT_HANDOFF.md` contains `## Current Work Log`.
- `AGENT_HANDOFF.md` contains `## Validation History`.
- `AGENT_HANDOFF.md` contains `## Task Backlog`.
- `AGENT_HANDOFF.md` reports a warning above the `32 KiB` soft limit and recommends multi layout above the `64 KiB` hard limit.

## Output Policy

The hook is advisory only. It explicitly returns `continue: true` and never emits a blocking decision.

It may use:

- `hookSpecificOutput.additionalContext` for startup and prompt-context injection.
- `systemMessage` for closeout, compaction, manual, or error reminders.
- `suppressOutput: true` for quiet no-op paths such as irrelevant `UserPromptSubmit`, active stop-loop suppression, and `SessionEnd`.

The hook should surface useful reminders without taking control away from the agent.

## Retry Policy

Retry only narrow failures that may be transient inside the current hook process:

- stdin read problems
- JSON parse problems from incomplete hook input

Repository state problems are not retried because retrying would not change them:

- missing handoff files
- missing required sections
- stale timestamps
- mixed or incomplete layout

Report repository state problems directly to the agent.

## Arguments And Environment

| Name | Purpose |
| --- | --- |
| `--project-dir <path>` | Set project root for manual testing. |
| `--event <name>` | Set the hook event when stdin is not provided. |
| `--max-age-minutes <n>` | Set stale handoff threshold. Default is `120`. |
| `CLAUDE_PROJECT_DIR` | Project root from Claude Code. Preferred over stdin `cwd`. |
| `HANDOFF_MAX_AGE_MINUTES=<n>` | Same as `--max-age-minutes <n>`. |

Manual test:

```bash
node .claude/hooks/handoff-watch.mjs --project-dir <repo-root> --event Stop
```

If stricter enforcement is desired, do not change this template to block by default. First confirm the desired behavior with the user and document the operational risk, because a blocking hook can interrupt normal closeout or startup.
