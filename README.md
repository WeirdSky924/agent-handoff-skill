# Agent Handoff Skill

<p align="center">
  <a href="README.md">中文</a> | <a href="README_en.md">English</a>
</p>

<p align="center">
  <a href="https://www.dsh.so/artifact/agent-handoff-skill/"><img src="https://www.dsh.so/badge/agent-handoff-skill.svg" alt="dsh.so security" /></a>
</p>

<p align="center">如果这个 skill 对你的 Agent 接力流程有帮助，欢迎给仓库点一个 Star，让更多人更容易找到它。</p>

![Agent Handoff Skill hero](assets/readme/hero.png)

一个给 Codex / Claude Code / DeepSeek Harness（DSH）使用的 **可持续接力机制 skill**。

它解决的问题很朴素：AI Agent 很强，但会话窗口不是可靠的项目记忆。上下文会压缩，会话会中断，Agent 会更换，开发任务却还要继续。`agent-handoff` 的目标就是把“上一位 Agent 脑子里的状态”沉淀成仓库内可维护、可验证、可接手的项目文档。

它不是聊天总结工具，也不是把所有历史都塞进一个 Markdown 文件。它更像一份轻量的“项目飞行记录仪”：记录当前目标、状态、活跃文件、关键决策、验证结果、风险、阻塞点和下一步，让下一位 Agent 能快速、安全地继续工作。现在它还包含确定性的容量治理脚本，避免 snapshot 和历史日志在长期使用后无限膨胀。

## 平台兼容性

这个仓库里的 skill 不是只给 Codex 用。它采用通用的 `SKILL.md + references/ + scripts/` 结构，可以按不同工具的发现路径安装：

| 平台 | 安装位置 | 触发方式 |
| --- | --- | --- |
| Codex | `~/.codex/skills/agent-handoff` | Codex 根据 skill 描述自动触发，或用户明确要求使用该 skill。 |
| Claude Code 个人级 Skill | `~/.claude/skills/agent-handoff` | Claude Code 自动发现，或用 `/agent-handoff` 显式调用。 |
| Claude Code 项目级 Skill | `<repo>/.claude/skills/agent-handoff` | 只对当前仓库生效，适合团队随仓库共享。 |
| DSH 个人级 Skill | `~/.dsh/skills/agent-handoff` | DSH 自动加入模型目录，也可用 `/agent-handoff` 显式调用。 |
| DSH 共享 Agent Skill | `~/.agents/skills/agent-handoff` | 使用 DSH 的共享 Agent Skills 根目录。 |
| DSH 项目级 Skill | `<repo>/.dsh/skills/agent-handoff` 或 `<repo>/.agents/skills/agent-handoff` | 只对当前 Git 仓库生效，项目目录优先于个人目录。 |

DSH 不会扫描 `~/.codex/skills`、`~/.claude/skills` 或 `<repo>/.claude/skills`，需要把仓库安装或链接到上表中的 DSH 根目录。安装到默认根目录不需要修改 DSH profile、patch 或 settings。当前仓库里的 `agents/openai.yaml` 是 Codex UI 元数据；Claude Code 和 DSH 会忽略它。

### dsh.so 市场元数据

仓库根目录的 `package.json` 是给 dsh.so 等目录服务读取的最小市场 manifest，包含 `name`、`license`、`description`、仓库地址和文件清单。它设置为 `private`，不代表这个 Skill 要发布到 npm，也不会改变 DSH 按 `SKILL.md` 发现和加载 Skill 的方式。

这个 manifest 主要解决 dsh.so 的 L2 结构化元数据检查；L3 还需要可解析的安装规范和声明的 DSH 版本，L4 才会在沙箱中实际安装。当前 Skill 不声明 npm 安装或 Cordis bundle 安装命令，因此不能把加入 `package.json` 误解为安装测试已经通过。

如果希望 dsh.so 通过 GitHub topic 自动识别仓库，可以在 GitHub 仓库设置中添加 `dsh-plugin` topic。这个 topic 是市场索引信号，不是 DSH profile 配置；当前仓库的实际运行入口仍然是 `SKILL.md`。

## 为什么会有这个 Skill

在长时间使用 AI Coding Agent 做真实项目时，常见断点通常不是“代码不会写”，而是这些更现实的问题：

- 新窗口打开后，Agent 不知道上一轮真正做到哪里。
- 上一位 Agent 做过技术决策，但没有记录原因和证据。
- 用户说“继续”，但当前目标、活跃文件、验证状态已经散落在旧聊天里。
- 一个复杂任务跨越多天、多模块、多次中断，最后没人能判断哪些内容已经完成。
- 接力文档越写越像聊天流水账，下一位 Agent 反而要读更多无关内容。
- 项目里有 `CLAUDE.md`、`AGENTS.md`、`.claude/CLAUDE.md` 等规则文件，但每个仓库的维护方式不一致。

`agent-handoff` 把这些经验固化为一个可复用 skill：它会指导 Agent 在仓库内创建或修复一套稳定的接力机制，并提供一个幂等 bootstrap 脚本，减少重复复制提示词和手工拼模板的错误。

它还会把更保守的文件读取协议写进项目规则：`Read` 范围默认不超过 240 行，`offset` 必须按行号处理，遇到 offset 漂移、空输出、stale snippet 或 API termination 时停止继续分页读取，并用搜索或只读 shell 命令重新锚定后再行动。

## 它创建什么

默认机制现在是 **多文档结构**，同时保留旧版单文档模式。

| 文件 | 作用 |
| --- | --- |
| `AGENT_HANDOFF.md` | 多文档模式下是入口索引和恢复路线；单文档模式下保存全部接力状态。 |
| `.agent-handoff/snapshot.md` | 多文档模式下保存当前目标、状态、下一步、活跃文件、阻塞点和开放问题。 |
| `.agent-handoff/workspace.md` | 项目结构、入口、测试命令、文档和长期项目背景。 |
| `.agent-handoff/decisions.md` | 重要决策、原因和证据。 |
| `.agent-handoff/work-log.md` | 近期仍有操作价值的工作日志。 |
| `.agent-handoff/validation.md` | 验证命令、结果、失败原因和未跑测试说明。 |
| `.agent-handoff/backlog.md` | 待办和 follow-up。 |
| `.agent-handoff/risks.md` | 风险、阻塞点、`UNKNOWN` 和需要确认的信息。 |
| `.agent-handoff/archive.md` | 压缩后的旧历史，不参与默认恢复。 |
| `.agent-handoff/archive/` | 自动轮换出的完整历史分片，单个文件不超过 128 KiB。 |
| `AGENTS.md` | Codex 与 DSH 共用的项目级 instructions 文件，写入平台中性的接力维护规则。 |
| `.claude/CLAUDE.md` | 项目级 Claude Code 规则，要求未来 Agent 启动时读取接力文档，并在收尾前更新。 |
| `AGENT_SESSION_PROMPTS.md` | 可选文件，保存新窗口启动、继续任务、收尾、接力质量审查等常用提示词。 |
| `.claude/settings.json` | 可选文件，仅在用户要求时合并安全的只读查询权限或 Claude Code 软提醒 hook 条目。 |
| `.claude/hooks/handoff-watch.mjs` | 可选 Claude Code hook 脚本，仅在显式使用 `--install-hooks` 时创建。 |
| `.gitignore` | 可选更新，把本地接力文档设为不提交，除非项目决定把它纳入版本控制。 |

核心约束是 **幂等**：项目级规则使用固定 marker 包裹。

```markdown
<!-- AGENT_HANDOFF_PROTOCOL:START -->
...
<!-- AGENT_HANDOFF_PROTOCOL:END -->
```

如果 marker 已存在，就替换区块；如果不存在，就追加区块；不会每次执行都重复堆一份规则。

## 它怎么工作

![Agent Handoff workflow](assets/readme/workflow.png)

`agent-handoff` 的运行逻辑可以理解为一个闭环：

1. **Inspect**：先看仓库结构，不直接写模板。
2. **Bootstrap**：创建或合并必要的接力文件和项目规则。
3. **Maintain**：任务过程中持续记录目标、决策、活跃文件、验证和风险。
4. **Compact / Rotate**：检查容量，先归档再压缩 snapshot，并按完整记录轮换过长日志。
5. **Closeout**：非纯聊天任务结束前，主动刷新并维护 `AGENT_HANDOFF.md` 或相关 `.agent-handoff/` 文件。
6. **Recover**：下一位 Agent 从接力文档恢复状态，再按需读取源码。

这个闭环的重点不是让 Agent 少读源码，而是让 Agent 少读无关历史。`AGENT_HANDOFF.md` 只负责告诉下一位 Agent “从哪里开始读”，具体实现仍然必须从源码和测试中验证。

多文档模式下，恢复读取顺序是：

1. `AGENT_HANDOFF.md`
2. `.agent-handoff/snapshot.md`
3. `.agent-handoff/risks.md`
4. `.agent-handoff/backlog.md`
5. `.agent-handoff/validation.md`，仅当验证状态影响当前任务
6. `.agent-handoff/decisions.md`，仅当要修改架构、行为、依赖或既有决策
7. `.agent-handoff/workspace.md`，仅当需要项目结构、命令或子项目边界
8. `.agent-handoff/work-log.md`，仅当需要近期实现细节
9. `.agent-handoff/archive.md`，仅当确实需要旧历史

## 主要应用场景

![Agent Handoff scenarios](assets/readme/scenarios.png)

### 1. 新项目初始化

当你打开一个新仓库，希望以后每个 Agent 都能自动维护接力状态，可以在 Codex、Claude Code 或 DSH 中使用这个 skill：

```text
使用 agent-handoff skill，为当前项目初始化接力机制。
```

它会检查仓库结构，创建 `AGENT_HANDOFF.md`，并按平台把 Durable Handoff 规则合并到：

- Codex / DSH：`AGENTS.md`
- Claude Code：`.claude/CLAUDE.md`

适合：

- 新 SaaS 项目
- 多模块 monorepo
- 需要长期维护的客户项目
- 经常切换 AI Agent 或会话窗口的仓库

### 2. 长任务跨窗口继续

一个功能开发可能跨越多次对话，例如：

- 第一天梳理架构和方案。
- 第二天实现后端 API。
- 第三天补前端和测试。
- 第四天修验证失败和边界条件。

如果没有接力机制，新 Agent 只能靠旧聊天恢复上下文。`AGENT_HANDOFF.md` 则会明确记录：

- 当前目标是什么。
- 哪些文件正在修改。
- 做过哪些决策。
- 跑过哪些验证命令。
- 哪些测试没跑，为什么没跑。
- 还有哪些风险和下一步。

继续任务时可以说：

```text
请读取 AGENT_HANDOFF.md，接着完成当前任务。
```

如果你遇到过 `Continue from where you left off.` 后 Agent 输出 `No response requested.` 或静默停止，可以使用更明确的继续提示：

```text
继续刚才的任务。不要回复 No response requested，也不要静默停止。请先说明你认为上一轮做到哪里、下一步具体动作是什么，然后继续执行。如果上下文不足，请读取 AGENT_HANDOFF.md 和必要的接力文件恢复状态。
```

### 3. Agent 更换或上下文压缩后恢复

当会话上下文被压缩，或者换了新的 Agent，最危险的是“看起来知道项目，实际上缺少关键状态”。这个 skill 的规则会要求新 Agent：

1. 先读取 `AGENT_HANDOFF.md`。
2. 明确当前目标、状态、下一步和阻塞点。
3. 只读取当前任务相关的源码。
4. 不把接力文档当作源码事实的替代品。

这样能降低两类常见风险：

- 新 Agent 重复做已经完成的工作。
- 新 Agent 基于过期或误解的上下文继续改代码。

### 4. 接力文档修复和瘦身

很多团队一开始会写接力文档，但写久了会变成：

- 聊天总结
- 长日志粘贴
- 没有路径的笼统描述
- 没有原因的决策
- 已经过期的待办
- 互相矛盾的状态

这时可以用：

```text
使用 agent-handoff skill，审查并修复当前项目的 AGENT_HANDOFF.md。
```

skill 会参考 `references/quality.md`，把文档重新整理成可接手的操作状态。

## 安装

### 方式一：作为 Codex 本地 Skill 使用

把仓库克隆或复制到你的 Codex skills 目录：

```powershell
git clone https://github.com/WeirdSky924/agent-handoff-skill C:\Users\<you>\.codex\skills\agent-handoff
```

如果你已经下载到本地，也可以复制：

```powershell
Copy-Item -Recurse -Force E:\_workspace\agent-handoff-skill C:\Users\<you>\.codex\skills\agent-handoff
```

然后在新的 Codex 会话里说：

```text
使用 agent-handoff skill，为当前项目初始化接力机制。
```

### 方式二：作为 Claude Code 个人级 Skill 使用

把仓库克隆或复制到 Claude Code 的个人级 skills 目录：

```powershell
git clone https://github.com/WeirdSky924/agent-handoff-skill C:\Users\<you>\.claude\skills\agent-handoff
```

如果你已经下载到本地：

```powershell
Copy-Item -Recurse -Force E:\_workspace\agent-handoff-skill C:\Users\<you>\.claude\skills\agent-handoff
```

然后在 Claude Code 中可以直接说：

```text
请使用 agent-handoff skill，为当前项目初始化接力机制。
```

或显式调用：

```text
/agent-handoff 为当前项目初始化接力机制
```

### 方式三：作为 Claude Code 项目级 Skill 使用

如果你希望团队成员拉取仓库后都能使用这个 skill，可以把它放进目标项目：

```powershell
mkdir .claude\skills
git clone https://github.com/WeirdSky924/agent-handoff-skill .claude\skills\agent-handoff
```

项目级安装适合团队标准化接力流程。个人级安装适合你在所有项目中复用。

### 方式四：作为 DeepSeek Harness Skill 使用

DSH 个人级安装：

```powershell
git clone https://github.com/WeirdSky924/agent-handoff-skill C:\Users\<you>\.dsh\skills\agent-handoff
```

也可以使用 DSH 支持的共享 Agent Skills 根目录：

```powershell
git clone https://github.com/WeirdSky924/agent-handoff-skill C:\Users\<you>\.agents\skills\agent-handoff
```

项目级安装：

```powershell
mkdir .dsh\skills
git clone https://github.com/WeirdSky924/agent-handoff-skill .dsh\skills\agent-handoff
```

DSH 会默认扫描这些目录，不需要修改 profile、`cordis.patch.yml` 或 `settings.yaml`。安装后可由模型自动加载，也可以显式输入：

```text
/agent-handoff 为当前项目初始化接力机制
```

### 方式五：只使用脚本

如果你不想注册为 skill，也可以直接运行脚本：

> `bootstrap_handoff.py` 和 `maintain_handoff.py` 需要 Python 3.10 或更高版本。DSH 本身只要求 Node.js，不保证系统已经安装 Python。

```powershell
python scripts\bootstrap_handoff.py --repo E:\path\to\your\repo --platform both --layout multi --session-prompts --gitignore
```

常用参数：

| 参数 | 说明 |
| --- | --- |
| `--repo <path>` | 目标仓库根目录，默认当前目录。 |
| `--platform codex\|claude\|dsh\|both` | 项目规则目标。`codex` 和 `dsh` 更新共用的 `AGENTS.md`，`claude` 更新 `.claude/CLAUDE.md`，`both` 写入两个文件并覆盖三个平台。 |
| `--layout single\|multi` | 接力结构。`multi` 是默认推荐模式；`single` 保留旧版单文档结构。 |
| `--session-prompts` | 如果缺失则创建 `AGENT_SESSION_PROMPTS.md`。 |
| `--gitignore` | 把 `AGENT_HANDOFF.md` 和 `AGENT_SESSION_PROMPTS.md` 加入 `.gitignore`。 |
| `--allow-readonly` | Claude Code 专用：合并安全只读查询权限到 `.claude/settings.json`。 |
| `--install-hooks` | Claude Code 专用：安装可选软提醒 hook，并把缺失 hook 条目合并到 `.claude/settings.json`。 |
| `--dry-run` | 只显示计划改动，不写入文件。 |
| `--skip-codex-rules` | 不创建或更新 Codex/DSH 共用的 `AGENTS.md`。 |
| `--skip-claude-rules` | 不创建或更新 `.claude/CLAUDE.md`。 |

示例：

```powershell
python scripts\bootstrap_handoff.py --repo E:\_workspace\my-saas --platform both --layout multi --session-prompts --gitignore --dry-run
```

确认输出后再去掉 `--dry-run`。

DSH-only 项目可以使用：

```powershell
python scripts\bootstrap_handoff.py --repo . --platform dsh --layout multi --dry-run
```

## 使用示例

### 初始化一个项目

用户：

```text
使用 agent-handoff skill，为当前项目建立可持续接力机制。
```

Agent 应该做：

1. 检查项目结构。
2. 查找已有 `CLAUDE.md`、`AGENTS.md`、`.claude/CLAUDE.md`。
3. 创建或更新 `AGENT_HANDOFF.md`。
4. 幂等合并 Codex / DSH 共用的 `AGENTS.md` handoff 区块。
5. 幂等合并 Claude Code `.claude/CLAUDE.md` 的 handoff 区块。
6. 可选创建 `AGENT_SESSION_PROMPTS.md`。
7. 复读修改后的文件。
8. 汇报创建了什么、当前状态是什么、还有哪些 `UNKNOWN`。

### 修复已有接力文档

用户：

```text
使用 agent-handoff skill，修复 AGENT_HANDOFF.md。它现在太长，而且状态有点乱。
```

Agent 应该做：

1. 读取 `references/quality.md`。
2. 读取当前 `AGENT_HANDOFF.md`。
3. 检查与仓库事实冲突的内容。
4. 压缩陈旧历史。
5. 刷新 Snapshot、Work Log、Validation History、Backlog。
6. 保留有证据的决策，删除聊天流水账。

### 为查询操作合并只读权限

用户：

```text
使用 agent-handoff skill，并让后续查询操作尽量不用手动审批。
```

Agent 可以运行：

```powershell
python scripts\bootstrap_handoff.py --repo . --allow-readonly
```

这只会在 Claude Code 的 `.claude/settings.json` 中合并安全的本地读取/搜索/检查权限，例如 `Read`、`Grep`、`Glob`、`rg`、`git status`、`git diff`。不会放行写入、删除、安装依赖、网络请求、启动服务或数据库变更。

### 安装 Claude Code 软提醒 Hook

用户：

```text
使用 agent-handoff skill，并为 Claude Code 添加接力 closeout 提醒 hook。
```

Agent 可以先 dry-run：

```powershell
python scripts\bootstrap_handoff.py --repo . --install-hooks --dry-run
```

确认后再执行：

```powershell
python scripts\bootstrap_handoff.py --repo . --install-hooks
```

这会创建 `.claude/hooks/handoff-watch.mjs`，并把 `SessionStart`、`UserPromptSubmit`、`PreCompact`、`Stop`、`SubagentStop`、`SessionEnd` 的缺失 hook 条目合并进 `.claude/settings.json`。该 hook 是事件感知的软提醒：启动时注入接力健康状态和恢复阅读顺序；用户说 `continue`、`resume`、`handoff`、`compact`、`closeout` 等相关内容时补充上下文；压缩前和收尾前提醒更新接力文档；发现 snapshot 或日志超过容量阈值时提示 Agent 处理。它始终返回 `continue: true`，不返回 `decision: "block"` 或 `continue: false`，不调用 Python，不写接力文件，不会因为 `AGENT_HANDOFF.md` 缺失或脚本检查异常而终止会话。

### 检查容量、压缩 Snapshot 和轮换历史

长期运行的项目会不断产生验证记录和工作日志。如果只靠“尽量写短”这一句规则，snapshot 很容易重新变成聊天归档。新版提供独立维护脚本，让 Codex、Claude Code 和 DSH 使用同一套确定性策略：

```powershell
# 只读检查，不修改任何文件
python scripts\maintain_handoff.py --repo . --check

# 超限时压缩 snapshot，并轮换日志和已完成 backlog
python scripts\maintain_handoff.py --repo . --compact-if-needed

# 不处理 snapshot，只轮换符合条件的历史记录
python scripts\maintain_handoff.py --repo . --rotate
```

如果脚本从已安装 skill 运行，把 `scripts\maintain_handoff.py` 换成实际 skill 路径，例如 `~/.codex/skills/agent-handoff/scripts/maintain_handoff.py`、`~/.claude/skills/agent-handoff/scripts/maintain_handoff.py`、`~/.dsh/skills/agent-handoff/scripts/maintain_handoff.py` 或 `~/.agents/skills/agent-handoff/scripts/maintain_handoff.py`。

| 文件 | 软限制 / 触发条件 | 硬限制 / 上限 | 自动处理 |
| --- | --- | --- | --- |
| `snapshot.md` | 16 KiB 或 240 行 | 32 KiB 或 400 行 | 先归档原文，再保留当前状态、有限数量的下一步/活跃文件/问题和恢复摘要。 |
| `work-log.md` | 64 KiB 或 30 个日期段 | 保留至少一个最新完整日期段 | 按完整 `## YYYY-MM-DD` 段轮换旧记录。 |
| `validation.md` | 64 KiB 或 200 行表格记录 | 保留至少一条最新完整记录 | 按完整 Markdown 表格行轮换。 |
| `backlog.md` | 32 KiB | 32 KiB | 只归档可机械识别的 `[x]` 已完成项。 |
| `risks.md` | 32 KiB | 32 KiB | 不自动删除；报告给 Agent 做语义审查。 |
| 单文档 `AGENT_HANDOFF.md` | 32 KiB | 64 KiB | 超过硬限制时迁移为多文档，不做复杂的文件内自动轮换。 |
| `.agent-handoff/archive/*.md` | 按需生成 | 每个 128 KiB | 按 UTF-8 安全边界自动分片，并在 `archive.md` 中建立索引。 |

安全边界比“强行变小”更重要：snapshot 结构解析失败时脚本不会覆盖原文件；risks 需要理解语义，因此不会机械删除；所有可自动压缩的 snapshot 都先完整归档，再原子替换。`--check` 只读取，hook 也只提醒，真正写入只会发生在 Agent 明确运行 `--compact-if-needed` 或 `--rotate` 时。

## 目录结构

```text
agent-handoff/
  SKILL.md
  README.md
  README_en.md
  agents/
    openai.yaml
  assets/
    readme/
      hero.png
      workflow.png
      scenarios.png
  templates/
    claude-settings-hooks.json
    handoff-watch.mjs
  references/
    codex-rules.md
    claude-rules.md
    dsh-rules.md
    hooks.md
    quality.md
    templates.md
  scripts/
    bootstrap_handoff.py
    maintain_handoff.py
  package.json
  LICENSE
```

多文档模式会在目标项目中创建：

```text
AGENT_HANDOFF.md
.agent-handoff/
  snapshot.md
  workspace.md
  decisions.md
  work-log.md
  validation.md
  backlog.md
  risks.md
  archive.md
  archive/
    <type>-<timestamp>.md
```

各部分职责：

- `SKILL.md`：运行时入口。越短越好，只放触发说明、核心流程、资源导航和边界。
- `references/templates.md`：`AGENT_HANDOFF.md` 和 `AGENT_SESSION_PROMPTS.md` 模板。
- `references/codex-rules.md`：Codex / DSH 共用的 `AGENTS.md` handoff 规则区块。
- `references/claude-rules.md`：Claude Code `.claude/CLAUDE.md` handoff 规则区块。
- `references/dsh-rules.md`：DSH 的 Skill 发现目录、调用契约、共享 `AGENTS.md` 规则和运行时边界。
- `references/hooks.md`：可选 Claude Code 事件感知 hook 说明，必须始终以 `0` 退出，不返回 `decision: "block"` 或 `continue: false`，不写接力文件，不应阻断或关闭会话。
- `templates/claude-settings-hooks.json`：Claude Code `.claude/settings.json` hook 片段模板，供手动合并或脚本安装使用。
- `templates/handoff-watch.mjs`：Claude Code 事件感知接力提醒 hook 脚本模板。
- `references/quality.md`：审查、修复、压缩接力文档时使用的质量标准。
- `scripts/bootstrap_handoff.py`：保守的初始化脚本，负责创建缺失文件、多文档或单文档结构、幂等合并规则，并可按需安装 Claude Code 软提醒 hook。
- `scripts/maintain_handoff.py`：Codex、Claude Code 和 DSH 共用的容量检查、snapshot 压缩和历史轮换脚本。
- `package.json`：给 dsh.so 使用的私有市场 manifest，不改变 DSH 的 `SKILL.md` 发现逻辑。
- `LICENSE`：MIT 许可证，供用户和目录服务识别授权边界。
- `README.md` / `README_en.md`：GitHub 展示文档，不参与 skill 运行。

## 设计原则

### 1. 仓库事实优先

接力文档不能编造。无法确认的内容写 `UNKNOWN`，并留下后续确认方式。

错误写法：

```markdown
- 项目使用 Next.js 和 PostgreSQL。
```

如果没有检查源码或配置，更好的写法是：

```markdown
- UNKNOWN: Backend/database stack needs confirmation from repository files.
```

### 2. 状态比历史更重要

`AGENT_HANDOFF.md` 不是聊天记录。它应该优先回答：

- 当前目标是什么？
- 当前状态是什么？
- 下一步做什么？
- 哪些文件相关？
- 做过哪些重要决策？
- 验证结果是什么？
- 还有哪些风险？

### 3. 文档要能被下一位 Agent 快速消费

一个合格的接力文档应该让新 Agent 在几分钟内恢复任务，而不是读半小时历史。过期内容要压缩，矛盾内容要删除，长日志要总结。

### 4. 幂等更新，不重复堆叠

项目级规则用 marker 管理。再次执行初始化时，应该替换已有规则区块，而不是重复追加。

### 5. 不越权修改用户级配置

默认只修改当前项目内文件。不要自动修改用户级配置，例如 `~/.codex/AGENTS.md`、`~/.claude/CLAUDE.md`、DSH profile、`cordis.patch.yml` 或 `settings.yaml`，除非用户明确要求。把 Skill 安装到 DSH 默认发现目录本身不需要修改这些配置。

### 6. 稳定读取优先于盲目翻页

生成的 `AGENTS.md` 和 `.claude/CLAUDE.md` 会要求 Agent 以小范围、可锚定的方式读取文件。Read offset 必须当作行号；如果出现空输出、offset warning、行号不一致、`file is shorter than the provided offset` 或 Read 后 API termination，Agent 必须停止继续用 Read 翻页，改用 `rg -n`、`wc -l`、`sed -n` 等只读命令重新定位。

### 7. 当前状态有界，完整历史可追溯

`snapshot.md` 采用替换式语义，不把上一版 snapshot 继续追加到文件底部。达到软限制后，维护脚本先把原文写入带时间戳的 archive 分片，再生成有界的当前状态；如果无法安全解析，则原样保留并要求 Agent 修复。这样恢复入口始终轻量，同时历史仍然可追溯。

## 质量清单

一个好的 `AGENT_HANDOFF.md` 应该满足：

- 新 Agent 能快速知道当前目标和下一步。
- 文件路径能从仓库根目录定位。
- 当前状态、待办和阻塞点不矛盾。
- 重要决策有原因和证据。
- 验证历史说明跑过什么、结果如何、有什么限制。
- 没有密钥、长日志、完整代码块或聊天流水账。
- 不确定内容明确标为 `UNKNOWN`。
- 它减少无关阅读，但不替代源码验证。

多文档模式还必须满足：

- `AGENT_HANDOFF.md` 只是索引和读取路线，不堆任务日志。
- `snapshot.md` 是替换式当前状态，通常不超过 16 KiB / 240 行，且不会在无提示的情况下超过 32 KiB / 400 行。
- `risks.md` 包含所有仍有效的风险、阻塞和 `UNKNOWN`。
- `backlog.md` 是可执行待办，不保留已完成旧项。
- `validation.md` 清楚记录 passed、failed、not run。
- `decisions.md` 的每个决策都有原因和证据。
- `work-log.md` 不超过 64 KiB / 30 个日期段，`validation.md` 不超过 64 KiB / 200 条记录。
- `backlog.md` 和 `risks.md` 不超过 32 KiB；自动归档不会删除待办或风险语义。
- 自动归档分片不超过 128 KiB，且默认恢复不需要读取它们。
- 新 Agent 只读入口索引、snapshot、risks、backlog、必要 validation/decisions，就能恢复前一个 Agent 的工作状态。

## 注意事项

- 如果项目决定把 `AGENT_HANDOFF.md` 提交进 Git，应谨慎记录内容，避免私密上下文、路径、日志或内部信息泄露。
- 如果项目把接力文档放进 `.gitignore`，要确保团队知道它是本地状态文件。
- hook 只是可选增强，不应该替代 Agent 自己的 closeout 责任；默认初始化不会安装 hook，只有显式使用 `--install-hooks` 才会写入 `.claude/hooks/handoff-watch.mjs` 并合并 `.claude/settings.json`。当前 hook 覆盖 `SessionStart`、`UserPromptSubmit`、`PreCompact`、`Stop`、`SubagentStop`、`SessionEnd`，只输出软上下文或软提醒。
- hook 只检测容量并提示，不会自动运行维护脚本；这避免 PostToolUse 或 Stop 阶段因 Python 进程、文件锁或脚本异常阻塞会话。
- Claude Code hook 不适用于 Codex 或 DSH；DSH 通过共享 `AGENTS.md` 执行恢复和 closeout 约束。
- 如果目标项目已有无 Agent handoff marker 的 `.claude/hooks/handoff-watch.mjs`，脚本会保留它且不会自动把 settings 指向该未知脚本，避免误接入可能阻断会话的自定义 hook。
- `bootstrap_handoff.py` 不会覆盖已有 `AGENT_HANDOFF.md`，因为已有接力状态必须由 Agent 基于仓库事实修复。
- DSH 目前仍处于 developer preview，后续版本可能调整 Skill 发现或指令加载契约；升级 DSH 后应对照 `references/dsh-rules.md` 中的官方链接重新核验。
- dsh.so 是独立的社区目录，不隶属于 DeepSeek AI；安全徽章代表其自动化静态扫描结果，不等同于人工安全审计或 DSH 官方认证。

## License

本仓库采用 MIT License，详见 `LICENSE` 文件。
