---
name: agent-handoff
description: Cross-platform skill for Codex, Claude Code, and DeepSeek Harness (DSH) that creates, updates, compacts, rotates, repairs, and reviews durable repository handoffs. Use when bootstrapping cross-session memory; creating or maintaining AGENT_HANDOFF.md and .agent-handoff files; adding AGENTS.md or .claude/CLAUDE.md rules; enforcing continuation recovery or closeout; managing oversized snapshots and logs; installing optional Claude advisory hooks; or reviewing handoff quality.
---

# Agent Handoff

## Overview

Use this cross-platform skill in Codex, Claude Code, or DeepSeek Harness (DSH) to establish repository-local continuity memory so a future agent can recover objective, status, decisions, validation, risks, and next actions without relying on previous chat history.

The handoff mechanism is repository-local by default. Do not edit user-level Codex, Claude Code, or DSH instructions, profiles, or settings unless the user explicitly asks for it.

## Platform Installation

- Codex personal skill: install this folder at `~/.codex/skills/agent-handoff`.
- Claude Code personal skill: install this folder at `~/.claude/skills/agent-handoff`.
- Claude Code project skill: install this folder at `<repo>/.claude/skills/agent-handoff`.
- DSH personal skill: install this folder at `~/.dsh/skills/agent-handoff`.
- DSH shared-agent skill: install this folder at `~/.agents/skills/agent-handoff`.
- DSH project skill: install this folder at `<repo>/.dsh/skills/agent-handoff` or `<repo>/.agents/skills/agent-handoff`.

DSH does not discover `~/.codex/skills`, `~/.claude/skills`, or `<repo>/.claude/skills`; install or link the bundle into one of its roots above. The same `SKILL.md`, `references/`, and `scripts/` are shared across platforms. `agents/openai.yaml` is Codex UI metadata and is ignored by Claude Code and DSH.

## Runtime Prerequisites

- Reading and applying the Markdown instructions requires no extra runtime beyond the host agent.
- Running `scripts/bootstrap_handoff.py` or `scripts/maintain_handoff.py` requires Python 3.10 or newer.
- DSH itself requires Node.js but does not guarantee Python. When Python is unavailable, create or repair files manually from `references/templates.md` and perform capacity review from `references/quality.md`.

## Layout Choice

- `multi` layout is the default for real projects. It creates `AGENT_HANDOFF.md` as a short index and `.agent-handoff/*.md` for state files.
- `single` layout is the legacy compact mode for small projects. It keeps all recovery state in `AGENT_HANDOFF.md`.
- Do not force-migrate an existing `AGENT_HANDOFF.md`. If it exists, preserve it and repair or migrate manually from repository facts.

## Workflow

1. Inspect the repository before writing files.
2. Identify existing agent guidance files: `AGENTS.md`, `CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/rules/`, `.claude/settings.json`, README files, docs, source roots, test configuration, and obvious subprojects.
3. If bootstrapping a new mechanism, prefer running `scripts/bootstrap_handoff.py` from this skill to create safe scaffolding and idempotent project handoff rule blocks.
4. If repairing or reviewing an existing mechanism, read `references/quality.md`, inspect the current files, then edit the repository files directly with factual updates.
5. Always keep the handoff content evidence-based. Use `UNKNOWN` for facts that cannot be verified from the repository or user request.
6. For multi layout, run `scripts/maintain_handoff.py --repo <repo-root> --compact-if-needed` after meaningful handoff updates and before closeout.
7. Re-read files you created or changed before reporting completion.

## Default Files

- `AGENT_HANDOFF.md`: Required durable handoff state at the repository root.
- `.agent-handoff/`: Multi-document layout directory for snapshot, workspace, decisions, work log, validation, backlog, risks, and archive.
- `AGENTS.md`: Recommended shared Codex and DSH project instructions file. Merge a marked handoff protocol block; do not overwrite unrelated project guidance.
- `.claude/CLAUDE.md`: Recommended project-level Claude Code rules generated for repositories that use Claude Code. Merge a marked handoff protocol block; do not overwrite unrelated rules.
- `AGENT_SESSION_PROMPTS.md`: Optional reusable prompts for new window startup, continuation, closeout, and quality review.
- `.gitignore`: Optionally add local handoff files when the project does not want to commit them.
- `.claude/settings.json`: Claude Code only. Optionally merge safe read-only permission allow rules or advisory handoff hooks if the user explicitly asks.
- `.claude/hooks/handoff-watch.mjs`: Claude Code only. Optional event-aware advisory hook script installed only when the user asks for hook reminders.

## Idempotency Rules

Use these markers for Codex/DSH `AGENTS.md` and Claude Code `.claude/CLAUDE.md` project-level handoff rules:

```markdown
<!-- AGENT_HANDOFF_PROTOCOL:START -->
...
<!-- AGENT_HANDOFF_PROTOCOL:END -->
```

If both markers already exist, replace only the content between them. If the target file exists without markers, append the marked block after the existing content. Never duplicate the protocol block.

Do not overwrite an existing `AGENT_HANDOFF.md` with a template. Existing handoff state must be repaired by reading repository facts and editing stale or missing sections.

## Bootstrap Script

Use the script for deterministic setup:

```bash
python <skill-dir>/scripts/bootstrap_handoff.py --repo <repo-root> --platform both --layout multi --session-prompts --gitignore
```

Useful flags:

- `--repo <path>`: Target repository root. Defaults to the current working directory.
- `--platform codex|claude|dsh|both`: Project rule target. `codex` and `dsh` update the shared `AGENTS.md`; `claude` updates `.claude/CLAUDE.md`; `both` updates both files and therefore covers all three hosts.
- `--layout single|multi`: Handoff structure. `multi` is default; `single` preserves the legacy single-file layout.
- `--session-prompts`: Create `AGENT_SESSION_PROMPTS.md` if missing.
- `--gitignore`: Add local handoff files to `.gitignore` if missing.
- `--allow-readonly`: Claude Code only. Merge safe read-only query permissions into `.claude/settings.json`.
- `--install-hooks`: Claude Code only. Install event-aware advisory handoff hook script and merge missing hook entries into `.claude/settings.json`. Hooks always exit `0`, never block, never write handoff files, and only emit soft `hookSpecificOutput.additionalContext` or `systemMessage` reminders when needed.
- `--skip-codex-rules`: Do not create or update the shared Codex / DSH `AGENTS.md` rules. The legacy flag name is retained for compatibility.
- `--skip-claude-rules`: Do not create or update `.claude/CLAUDE.md`.
- `--dry-run`: Show planned changes without writing files.

After running the script, inspect the generated files and replace placeholder or `UNKNOWN` content with repository-based facts where possible.

## Maintenance Script

Use the deterministic maintenance script for multi-document capacity control:

```bash
python <skill-dir>/scripts/maintain_handoff.py --repo <repo-root> --check
python <skill-dir>/scripts/maintain_handoff.py --repo <repo-root> --compact-if-needed
python <skill-dir>/scripts/maintain_handoff.py --repo <repo-root> --rotate
```

- `--check` is read-only and reports soft warnings or unresolved hard-limit findings.
- `--compact-if-needed` archives and normalizes an oversized parseable snapshot, then rotates oversized work-log, validation, and completed backlog records.
- `--rotate` skips snapshot compaction and rotates only eligible history records.
- Never rewrite an unparseable snapshot. Never delete risks mechanically. Preserve complete work-log sections and validation rows.
- The Claude hook does not run this script. It only reports capacity warnings and always remains read-only and non-blocking.

Capacity policy:

- Snapshot soft limit: `16 KiB` or `240` lines.
- Snapshot hard limit: `32 KiB` or `400` lines.
- Work log: `64 KiB` or `30` dated sections.
- Validation history: `64 KiB` or `200` table rows.
- Backlog and risks: `32 KiB` each.
- Generated archive chunks: at most `128 KiB` each.
- Legacy single layout: `32 KiB` soft limit and `64 KiB` hard limit; migrate to multi layout rather than adding complex in-file rotation.

## Multi-Document Recovery Contract

In `multi` layout, a new agent must recover in this order:

1. `AGENT_HANDOFF.md`
2. `.agent-handoff/snapshot.md`
3. `.agent-handoff/risks.md`
4. `.agent-handoff/backlog.md`
5. `.agent-handoff/validation.md` when validation state matters
6. `.agent-handoff/decisions.md` when changing durable behavior or architecture
7. `.agent-handoff/workspace.md` when orientation or commands are needed
8. `.agent-handoff/work-log.md` when recent implementation details are needed
9. `.agent-handoff/archive.md` only for old context

`snapshot.md` is replace-in-place current state, not append-only history. Keep it short and action-oriented; use the dedicated files for decisions, validation, backlog, risks, and history. Archive the original before deterministic normalization, and leave the file unchanged when safe parsing is impossible.

## References

Load only the references needed for the task:

- `references/templates.md`: Read when creating or manually repairing `AGENT_HANDOFF.md` or `AGENT_SESSION_PROMPTS.md`.
- `references/codex-rules.md`: Read when creating or updating the shared Codex / DSH `AGENTS.md` block.
- `references/claude-rules.md`: Read when creating or updating Claude Code `.claude/CLAUDE.md`.
- `references/dsh-rules.md`: Read when installing for DSH or checking DSH discovery and runtime boundaries.
- `references/hooks.md`: Read only when the user asks for hook-based enforcement.
- `references/quality.md`: Read when reviewing, compressing, repairing, or validating a handoff mechanism.
- `templates/claude-settings-hooks.json`: Claude Code hook settings snippet for manual review or installation.
- `templates/handoff-watch.mjs`: Claude Code event-aware advisory hook script template.
- `scripts/maintain_handoff.py`: Cross-platform read-only checks plus explicit snapshot compaction and history rotation.

## Closeout

When this skill changes repository files, report:

- Files created or updated.
- Current handoff status.
- How the next agent should start.
- Any remaining `UNKNOWN` entries, risks, or user confirmations needed.
