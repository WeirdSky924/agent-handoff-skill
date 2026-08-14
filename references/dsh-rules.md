# DeepSeek Harness Handoff Rules

Use this reference when installing `agent-handoff` for DeepSeek Harness (DSH) or generating project rules that DSH can load.

DSH is currently a developer preview and may make compatibility-breaking changes. This guidance follows the official `deepseek-ai/deepseek-harness` filesystem-skill and agent-instructions contracts available when this reference was updated.

## Skill Discovery

DSH scans these roots in priority order:

1. `<project-root>/.dsh/skills`
2. `<project-root>/.agents/skills`
3. Configured custom skill roots
4. `~/.dsh/skills`
5. `~/.agents/skills`

Install this repository as a one-level directory bundle named `agent-handoff`:

```text
<skill-root>/agent-handoff/SKILL.md
<skill-root>/agent-handoff/references/
<skill-root>/agent-handoff/scripts/
<skill-root>/agent-handoff/assets/
```

DSH does not discover `~/.codex/skills`, `~/.claude/skills`, or `<project>/.claude/skills`. Installing or linking the bundle into a default DSH root requires no DSH profile or settings change.

Examples:

```powershell
git clone https://github.com/WeirdSky924/agent-handoff-skill "$HOME\.dsh\skills\agent-handoff"
git clone https://github.com/WeirdSky924/agent-handoff-skill ".dsh\skills\agent-handoff"
```

Use `~/.agents/skills/agent-handoff` or `<project>/.agents/skills/agent-handoff` when a shared Agent Skills root is preferred.

## Skill Contract

The repository already uses DSH-compatible skill primitives:

- A one-level `<name>/SKILL.md` bundle.
- YAML frontmatter with required kebab-case `name` and non-empty `description`.
- Relative `references/`, `scripts/`, and `assets/` resources.
- Omitted `disable-model-invocation` and `user-invocable`, which lets both the model and the user invoke the skill.

The DSH catalog shows at most 500 description characters by default. Keep this skill's frontmatter description within that bound so routing guidance is not truncated.

## Project Rules

DSH loads project `AGENTS.md` and `CLAUDE.md` instruction files. Generate only the shared root `AGENTS.md` rules for a DSH-only repository:

```bash
python <skill-dir>/scripts/bootstrap_handoff.py --repo <repo-root> --platform dsh --layout multi
```

`--platform dsh` does not create `.claude/CLAUDE.md` and does not modify DSH configuration. The generated marker block is platform-neutral so the same `AGENTS.md` can be consumed by Codex and DSH.

Use `--platform both` when Codex, Claude Code, and DSH share the repository. It writes the shared `AGENTS.md` plus Claude Code's `.claude/CLAUDE.md`.

## Runtime Requirements

DSH itself requires Node.js, but it does not guarantee Python. Running `bootstrap_handoff.py` or `maintain_handoff.py` requires Python 3.10 or newer. Without Python, use `references/templates.md` and `references/quality.md` to perform the same repository-local work manually.

## Hook Boundary

The optional `.claude/hooks/handoff-watch.mjs` and `.claude/settings.json` integration is Claude Code specific. DSH does not use that hook configuration. Do not install Claude hooks for a DSH-only project; rely on the shared `AGENTS.md` closeout protocol unless a separate DSH plugin is explicitly requested.

## Official Sources

- [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)
- [Filesystem skill provider](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/skill/skill-filesystem)
- [Skill subsystem](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md)
- [Agent instructions](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/context/agent-instructions)
