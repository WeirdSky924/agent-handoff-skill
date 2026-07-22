#!/usr/bin/env node
// AGENT_HANDOFF_HOOK:START
import fs from "node:fs";
import path from "node:path";

const MULTI_FILES = [
  "snapshot.md",
  "workspace.md",
  "decisions.md",
  "work-log.md",
  "validation.md",
  "backlog.md",
  "risks.md",
  "archive.md"
];

const SINGLE_HEADINGS = [
  "## Handoff Snapshot",
  "## Current Work Log",
  "## Validation History",
  "## Task Backlog"
];

const PROMPT_TRIGGERS = [
  "handoff",
  "agent_handoff",
  "continue",
  "resume",
  "closeout",
  "compact",
  "handover",
  "recover",
  "resume work",
  "session state",
  "restore context"
];

const DEFAULT_MAX_AGE_MINUTES = 120;
const MAX_READ_BYTES = 512 * 1024;
const INPUT_RETRY_LIMIT = 2;
const SNAPSHOT_SOFT_BYTES = 16 * 1024;
const SNAPSHOT_SOFT_LINES = 240;
const SNAPSHOT_HARD_BYTES = 32 * 1024;
const SNAPSHOT_HARD_LINES = 400;
const WORK_LOG_MAX_BYTES = 64 * 1024;
const WORK_LOG_MAX_SECTIONS = 30;
const VALIDATION_MAX_BYTES = 64 * 1024;
const VALIDATION_MAX_ROWS = 200;
const CURRENT_STATE_MAX_BYTES = 32 * 1024;
const SINGLE_SOFT_BYTES = 32 * 1024;
const SINGLE_HARD_BYTES = 64 * 1024;

function optionValue(name) {
  const flag = `--${name}`;
  const exact = process.argv.find((arg) => arg.startsWith(`${flag}=`));
  if (exact) return exact.slice(flag.length + 1);
  const index = process.argv.indexOf(flag);
  if (index !== -1 && index + 1 < process.argv.length) return process.argv[index + 1];
  return undefined;
}

function sleep(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

function exists(filePath) {
  try {
    return fs.existsSync(filePath);
  } catch {
    return false;
  }
}

function isDirectory(filePath) {
  try {
    return fs.statSync(filePath).isDirectory();
  } catch {
    return false;
  }
}

function readSmallText(filePath) {
  try {
    const stat = fs.statSync(filePath);
    if (stat.size > MAX_READ_BYTES) {
      const handle = fs.openSync(filePath, "r");
      try {
        const buffer = Buffer.alloc(MAX_READ_BYTES);
        const bytesRead = fs.readSync(handle, buffer, 0, MAX_READ_BYTES, 0);
        return buffer.subarray(0, bytesRead).toString("utf8");
      } finally {
        fs.closeSync(handle);
      }
    }
    return fs.readFileSync(filePath, "utf8");
  } catch {
    return "";
  }
}

function readHookInputWithRetry() {
  if (process.stdin.isTTY) return { input: {}, parseWarning: null };

  let lastWarning = null;
  for (let attempt = 0; attempt <= INPUT_RETRY_LIMIT; attempt += 1) {
    try {
      const raw = fs.readFileSync(0, "utf8").trim();
      if (!raw) return { input: {}, parseWarning: lastWarning };
      return { input: JSON.parse(raw), parseWarning: null };
    } catch (error) {
      const retryable = error instanceof SyntaxError || error.code === "EAGAIN";
      lastWarning = retryable
        ? `Hook stdin read/parse issue after attempt ${attempt + 1}: ${error.message}`
        : `Could not read hook stdin: ${error.message}`;
      if (!retryable || attempt === INPUT_RETRY_LIMIT) {
        return { input: {}, parseWarning: lastWarning };
      }
      sleep(20 * (attempt + 1));
    }
  }

  return { input: {}, parseWarning: lastWarning };
}

function ageMinutes(filePath) {
  try {
    const stat = fs.statSync(filePath);
    return Math.max(0, Math.round((Date.now() - stat.mtimeMs) / 60000));
  } catch {
    return null;
  }
}

function fileSize(filePath) {
  try {
    return fs.statSync(filePath).size;
  } catch {
    return null;
  }
}

function countLines(text) {
  if (!text) return 0;
  const lines = text.split(/\r?\n/);
  return lines.at(-1) === "" ? lines.length - 1 : lines.length;
}

function addMultiCapacityWarnings(health) {
  const snapshotPath = path.join(health.handoffDir, "snapshot.md");
  const snapshotSize = fileSize(snapshotPath);
  if (snapshotSize !== null) {
    const snapshotLines = countLines(readSmallText(snapshotPath));
    const metrics = `${snapshotSize} bytes, ${snapshotLines} lines`;
    if (snapshotSize > SNAPSHOT_HARD_BYTES || snapshotLines > SNAPSHOT_HARD_LINES) {
      health.warnings.push(
        `snapshot.md exceeds the 32 KiB / 400 line hard limit (${metrics}); run handoff maintenance before closeout.`
      );
    } else if (snapshotSize > SNAPSHOT_SOFT_BYTES || snapshotLines > SNAPSHOT_SOFT_LINES) {
      health.warnings.push(
        `snapshot.md exceeds the 16 KiB / 240 line soft limit (${metrics}); compact it before closeout.`
      );
    }
  }

  const workLogPath = path.join(health.handoffDir, "work-log.md");
  const workLogSize = fileSize(workLogPath);
  if (workLogSize !== null) {
    const sections = (readSmallText(workLogPath).match(/^## \d{4}-\d{2}-\d{2}(?:\b|\s)/gm) || []).length;
    if (workLogSize > WORK_LOG_MAX_BYTES || sections > WORK_LOG_MAX_SECTIONS) {
      health.warnings.push(
        `work-log.md exceeds 64 KiB or ${WORK_LOG_MAX_SECTIONS} dated sections; rotate old complete sections.`
      );
    }
  }

  const validationPath = path.join(health.handoffDir, "validation.md");
  const validationSize = fileSize(validationPath);
  if (validationSize !== null) {
    const tableRows = Math.max(
      0,
      readSmallText(validationPath).split(/\r?\n/).filter((line) => line.trimStart().startsWith("|")).length - 2
    );
    if (validationSize > VALIDATION_MAX_BYTES || tableRows > VALIDATION_MAX_ROWS) {
      health.warnings.push(
        `validation.md exceeds 64 KiB or ${VALIDATION_MAX_ROWS} rows; rotate old complete rows.`
      );
    }
  }

  for (const name of ["backlog.md", "risks.md"]) {
    const size = fileSize(path.join(health.handoffDir, name));
    if (size !== null && size > CURRENT_STATE_MAX_BYTES) {
      health.warnings.push(`${name} exceeds the 32 KiB current-state limit; Agent review is required.`);
    }
  }
}

function containsAny(text, terms) {
  const lower = text.toLowerCase();
  return terms.some((term) => lower.includes(term.toLowerCase()));
}

function buildHealth(projectDir, maxAgeMinutes, parseWarning) {
  const handoffPath = path.join(projectDir, "AGENT_HANDOFF.md");
  const handoffDir = path.join(projectDir, ".agent-handoff");
  const content = exists(handoffPath) ? readSmallText(handoffPath) : "";
  const health = {
    projectDir,
    layout: "missing",
    handoffPath,
    handoffDir,
    ageMinutes: exists(handoffPath) ? ageMinutes(handoffPath) : null,
    critical: [],
    warnings: [],
    missing: []
  };

  if (parseWarning) health.warnings.push(parseWarning);

  if (!exists(handoffPath)) {
    health.critical.push("AGENT_HANDOFF.md is missing.");
    return health;
  }

  if (isDirectory(handoffDir)) {
    health.layout = "multi";

    for (const rel of MULTI_FILES) {
      if (!exists(path.join(handoffDir, rel))) {
        health.missing.push(`.agent-handoff/${rel}`);
      }
    }

    if (!content.includes("## Recovery Reading Order")) {
      health.critical.push(
        "Multi-document layout exists, but AGENT_HANDOFF.md does not contain '## Recovery Reading Order'."
      );
    }

    if (!content.includes("## Handoff Layout")) {
      health.warnings.push("AGENT_HANDOFF.md does not contain '## Handoff Layout'.");
    }

    const snapshot = readSmallText(path.join(handoffDir, "snapshot.md"));
    if (snapshot && !snapshot.includes("## Current State")) {
      health.warnings.push(".agent-handoff/snapshot.md does not contain '## Current State'.");
    }
    addMultiCapacityWarnings(health);
  } else {
    health.layout = "single";

    for (const heading of SINGLE_HEADINGS) {
      if (!content.includes(heading)) {
        health.missing.push(heading);
      }
    }

    const handoffSize = fileSize(handoffPath);
    if (handoffSize !== null && handoffSize > SINGLE_HARD_BYTES) {
      health.warnings.push(
        `AGENT_HANDOFF.md exceeds the 64 KiB single-layout hard limit (${handoffSize} bytes); migrate to multi layout.`
      );
    } else if (handoffSize !== null && handoffSize > SINGLE_SOFT_BYTES) {
      health.warnings.push(
        `AGENT_HANDOFF.md exceeds the 32 KiB single-layout soft limit (${handoffSize} bytes).`
      );
    }
  }

  if (health.missing.length > 0) {
    health.critical.push(`Missing expected handoff structure: ${health.missing.join(", ")}.`);
  }

  if (health.ageMinutes !== null && health.ageMinutes > maxAgeMinutes) {
    health.warnings.push(
      `AGENT_HANDOFF.md was last modified about ${health.ageMinutes} minutes ago.`
    );
  }

  return health;
}

function recoveryHint(health) {
  if (health.layout === "multi") {
    return [
      "Read AGENT_HANDOFF.md first.",
      "Then read .agent-handoff/snapshot.md, .agent-handoff/risks.md, and .agent-handoff/backlog.md.",
      "Read validation, decisions, workspace, work-log, and archive only when task-relevant."
    ].join(" ");
  }

  if (health.layout === "single") {
    return "Read AGENT_HANDOFF.md first, then inspect only task-relevant source files.";
  }

  return "Create or repair AGENT_HANDOFF.md before relying on repository handoff memory.";
}

function healthSummary(health) {
  const parts = [
    `Agent handoff health: layout=${health.layout}`,
    health.ageMinutes === null ? "age=unknown" : `age=${health.ageMinutes}m`
  ];

  if (health.critical.length) parts.push(`critical=${health.critical.join(" ")}`);
  if (health.warnings.length) parts.push(`warnings=${health.warnings.join(" ")}`);
  parts.push(recoveryHint(health));
  return parts.join(" ");
}

function writeJson(output) {
  process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
}

function contextOutput(eventName, context, suppressOutput = false) {
  return {
    continue: true,
    suppressOutput,
    hookSpecificOutput: {
      hookEventName: eventName,
      additionalContext: context
    }
  };
}

function systemOutput(message, suppressOutput = false) {
  return {
    continue: true,
    suppressOutput,
    systemMessage: message
  };
}

const { input, parseWarning } = readHookInputWithRetry();
const eventName = input.hook_event_name || optionValue("event") || "Manual";
const maxAgeMinutes = Number.parseInt(
  process.env.HANDOFF_MAX_AGE_MINUTES || optionValue("max-age-minutes") || `${DEFAULT_MAX_AGE_MINUTES}`,
  10
);
const projectDir = path.resolve(
  optionValue("project-dir") ||
    process.env.CLAUDE_PROJECT_DIR ||
    input.cwd ||
    process.cwd()
);
const health = buildHealth(
  projectDir,
  Number.isFinite(maxAgeMinutes) ? maxAgeMinutes : DEFAULT_MAX_AGE_MINUTES,
  parseWarning
);
const summary = healthSummary(health);

try {
  switch (eventName) {
    case "SessionStart": {
      writeJson(contextOutput("SessionStart", summary, false));
      break;
    }

    case "UserPromptSubmit": {
      const prompt = String(input.prompt || "");
      if (health.critical.length > 0 || containsAny(prompt, PROMPT_TRIGGERS)) {
        writeJson(contextOutput("UserPromptSubmit", summary, false));
      } else {
        writeJson({ continue: true, suppressOutput: true });
      }
      break;
    }

    case "PreCompact": {
      writeJson(
        systemOutput(
          `${summary} Before compaction, update handoff files if the current task state changed.`,
          false
        )
      );
      break;
    }

    case "Stop":
    case "SubagentStop": {
      if (input.stop_hook_active) {
        writeJson({ continue: true, suppressOutput: true });
        break;
      }

      writeJson(
        systemOutput(
          `${summary} If repository state changed, update the relevant handoff files before final response.`,
          false
        )
      );
      break;
    }

    case "SessionEnd": {
      writeJson(systemOutput(`Session ending. ${summary}`, true));
      break;
    }

    default: {
      writeJson(systemOutput(summary, false));
      break;
    }
  }
} catch (error) {
  writeJson(
    systemOutput(
      `Handoff hook failed softly: ${error.message}. Manually verify AGENT_HANDOFF.md before closeout.`,
      false
    )
  );
}
// AGENT_HANDOFF_HOOK:END
