#!/usr/bin/env python3
"""Check, compact, and rotate repository-local Agent handoff state."""

from __future__ import annotations

import argparse
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


SNAPSHOT_SOFT_BYTES = 16 * 1024
SNAPSHOT_SOFT_LINES = 240
SNAPSHOT_HARD_BYTES = 32 * 1024
SNAPSHOT_HARD_LINES = 400
WORK_LOG_MAX_BYTES = 64 * 1024
WORK_LOG_MAX_SECTIONS = 30
VALIDATION_MAX_BYTES = 64 * 1024
VALIDATION_MAX_ROWS = 200
CURRENT_STATE_MAX_BYTES = 32 * 1024
SINGLE_SOFT_BYTES = 32 * 1024
SINGLE_HARD_BYTES = 64 * 1024
ARCHIVE_CHUNK_BYTES = 128 * 1024

SNAPSHOT_LIST_LIMITS = {
    "Immediate next actions": 5,
    "Active files": 20,
    "Open questions": 10,
}
SNAPSHOT_SCALAR_FIELDS = {
    "Last updated",
    "Last agent",
    "Workspace root",
    "Current objective",
    "Current status",
    "Blockers",
}


@dataclass
class MaintenanceResult:
    changed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)

    def merge(self, other: "MaintenanceResult") -> None:
        self.changed.extend(other.changed)
        self.warnings.extend(other.warnings)
        self.unresolved.extend(other.unresolved)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def byte_count(text: str) -> int:
    return len(text.encode("utf-8"))


def line_count(text: str) -> int:
    return len(text.splitlines())


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            delete=False,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(content)
            temp_path = Path(handle.name)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def unique_items(items: list[str], limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = item.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
        if len(result) == limit:
            break
    return result


def split_utf8(text: str, max_bytes: int) -> list[str]:
    if byte_count(text) <= max_bytes:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_bytes = 0
    for line in text.splitlines(keepends=True):
        encoded = line.encode("utf-8")
        if len(encoded) > max_bytes:
            if current:
                chunks.append("".join(current))
                current = []
                current_bytes = 0
            segment = ""
            for char in line:
                candidate = segment + char
                if byte_count(candidate) > max_bytes:
                    chunks.append(segment)
                    segment = char
                else:
                    segment = candidate
            if segment:
                current = [segment]
                current_bytes = byte_count(segment)
            continue
        if current and current_bytes + len(encoded) > max_bytes:
            chunks.append("".join(current))
            current = []
            current_bytes = 0
        current.append(line)
        current_bytes += len(encoded)
    if current:
        chunks.append("".join(current))
    return chunks


def append_archive_index(handoff_dir: Path, entries: list[tuple[Path, str]]) -> None:
    index_path = handoff_dir / "archive.md"
    content = read_text(index_path).rstrip()
    if not content:
        content = "# Handoff Archive\n\nThis file indexes compressed history outside normal recovery."
    if "## Rotated Records" not in content:
        content += "\n\n## Rotated Records"
    for path, reason in entries:
        relative = path.relative_to(handoff_dir).as_posix()
        link = f"- [{path.name}]({relative}): {reason}"
        if link not in content:
            content += f"\n{link}"
    atomic_write(index_path, content.rstrip() + "\n")


def archive_content(handoff_dir: Path, kind: str, content: str, reason: str) -> list[Path]:
    archive_dir = handoff_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    payload_limit = ARCHIVE_CHUNK_BYTES - 2048
    payloads = split_utf8(content, payload_limit)
    created: list[Path] = []
    for index, payload in enumerate(payloads, start=1):
        suffix = f"-part{index}" if len(payloads) > 1 else ""
        path = archive_dir / f"{kind}-{timestamp}{suffix}.md"
        archived = (
            f"# Archived {kind.replace('-', ' ').title()}\n\n"
            f"- Archived at: {datetime.now(timezone.utc).isoformat()}\n"
            f"- Reason: {reason}\n\n"
            "## Original Content\n\n"
            f"{payload.rstrip()}\n"
        )
        atomic_write(path, archived)
        created.append(path)
    append_archive_index(handoff_dir, [(path, reason) for path in created])
    return created


def h2_sections(text: str, title: str) -> list[str]:
    matches = list(re.finditer(r"(?m)^## ([^\r\n]+)\r?$", text))
    sections: list[str] = []
    for index, match in enumerate(matches):
        if match.group(1).strip() != title:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append(text[start:end].strip())
    return sections


def parse_snapshot(text: str) -> tuple[dict[str, str], dict[str, list[str]], list[str]]:
    current_sections = h2_sections(text, "Current State")
    if not current_sections:
        raise ValueError("snapshot is missing '## Current State'")

    scalars: dict[str, str] = {}
    lists = {key: [] for key in SNAPSHOT_LIST_LIMITS}
    active_list: str | None = None
    for line in current_sections[-1].splitlines():
        field_match = re.match(r"^- ([^:]+):\s*(.*)$", line)
        if field_match:
            key = field_match.group(1).strip()
            value = field_match.group(2).strip()
            if key in SNAPSHOT_LIST_LIMITS:
                active_list = key
                if value:
                    lists[key].append(value)
            elif key in SNAPSHOT_SCALAR_FIELDS:
                scalars[key] = value
                active_list = None
            else:
                active_list = None
            continue
        item_match = re.match(r"^\s{2,}-\s+(.+)$", line)
        if item_match and active_list:
            lists[active_list].append(item_match.group(1).strip())

    required = ["Current objective", "Current status"]
    missing = [key for key in required if not scalars.get(key)]
    if missing or not lists["Immediate next actions"]:
        details = ", ".join(missing + (["Immediate next actions"] if not lists["Immediate next actions"] else []))
        raise ValueError(f"snapshot is missing required current-state fields: {details}")

    recovery_sections = h2_sections(text, "Recovery Summary")
    recovery: list[str] = []
    if recovery_sections:
        for line in recovery_sections[-1].splitlines():
            match = re.match(r"^-\s+(.+)$", line)
            if match:
                recovery.append(match.group(1).strip())
    return scalars, lists, recovery


def truncate_utf8(value: str, max_bytes: int) -> str:
    marker = "... [truncated; see archive]"
    if byte_count(value) <= max_bytes:
        return value
    budget = max_bytes - byte_count(marker)
    if budget <= 0:
        return marker[:max_bytes]
    result: list[str] = []
    used = 0
    for char in value:
        size = byte_count(char)
        if used + size > budget:
            break
        result.append(char)
        used += size
    return "".join(result).rstrip() + marker


def render_snapshot(
    scalars: dict[str, str], lists: dict[str, list[str]], recovery: list[str]
) -> str:
    scalar_limits = {
        "Last updated": 256,
        "Last agent": 256,
        "Workspace root": 512,
        "Current objective": 768,
        "Current status": 768,
        "Blockers": 768,
    }
    lines = ["# Handoff Snapshot", "", "## Current State", ""]
    for key in ["Last updated", "Last agent", "Workspace root", "Current objective", "Current status"]:
        if key in scalars:
            lines.append(f"- {key}: {truncate_utf8(scalars[key], scalar_limits[key])}")

    for key in ["Immediate next actions", "Active files"]:
        lines.append(f"- {key}:")
        values = unique_items(lists[key], SNAPSHOT_LIST_LIMITS[key])
        lines.extend(f"  - {truncate_utf8(value, 256)}" for value in values)

    if "Blockers" in scalars:
        lines.append(f"- Blockers: {truncate_utf8(scalars['Blockers'], scalar_limits['Blockers'])}")

    lines.append("- Open questions:")
    questions = unique_items(lists["Open questions"], SNAPSHOT_LIST_LIMITS["Open questions"])
    lines.extend(f"  - {truncate_utf8(value, 256)}" for value in questions)

    recovery_items = unique_items(recovery, 5)
    if not recovery_items:
        recovery_items = ["Resume from the current objective and immediate next actions."]
    lines.extend(["", "## Recovery Summary", ""])
    lines.extend(f"- {truncate_utf8(item, 256)}" for item in recovery_items)
    return "\n".join(lines).rstrip() + "\n"


def exceeds_snapshot_soft_limit(text: str) -> bool:
    return byte_count(text) > SNAPSHOT_SOFT_BYTES or line_count(text) > SNAPSHOT_SOFT_LINES


def exceeds_snapshot_hard_limit(text: str) -> bool:
    return byte_count(text) > SNAPSHOT_HARD_BYTES or line_count(text) > SNAPSHOT_HARD_LINES


def maintain_snapshot(handoff_dir: Path) -> MaintenanceResult:
    result = MaintenanceResult()
    path = handoff_dir / "snapshot.md"
    if not path.exists():
        result.unresolved.append(".agent-handoff/snapshot.md is missing.")
        return result

    original = read_text(path)
    if not exceeds_snapshot_soft_limit(original):
        return result

    severity = "hard" if exceeds_snapshot_hard_limit(original) else "soft"
    try:
        scalars, lists, recovery = parse_snapshot(original)
    except ValueError as error:
        result.unresolved.append(
            f"Snapshot exceeds the {severity} limit but was preserved because it cannot be safely parsed: {error}."
        )
        return result

    compacted = render_snapshot(scalars, lists, recovery)
    if exceeds_snapshot_soft_limit(compacted):
        result.unresolved.append(
            "Snapshot normalization could not reduce the file below 16 KiB / 240 lines; original content was preserved."
        )
        return result

    reason = (
        f"snapshot exceeded the {severity} limit "
        f"({byte_count(original)} bytes, {line_count(original)} lines)"
    )
    archive_content(handoff_dir, "snapshot", original, reason)
    atomic_write(path, compacted)
    result.changed.append(".agent-handoff/snapshot.md")
    result.changed.append(".agent-handoff/archive.md")
    result.warnings.append(f"Compacted and archived an oversized snapshot: {reason}.")
    return result


def remove_spans(text: str, spans: list[tuple[int, int]]) -> str:
    if not spans:
        return text
    parts: list[str] = []
    cursor = 0
    for start, end in sorted(spans):
        parts.append(text[cursor:start])
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts)


def dated_h2_sections(text: str) -> list[tuple[int, int, str]]:
    headings = list(re.finditer(r"(?m)^## [^\r\n]+\r?$", text))
    sections: list[tuple[int, int, str]] = []
    for index, heading in enumerate(headings):
        title = heading.group(0)[3:].strip()
        if not re.match(r"^\d{4}-\d{2}-\d{2}(?:\b|\s)", title):
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        sections.append((heading.start(), end, text[heading.start():end]))
    return sections


def maintain_work_log(handoff_dir: Path) -> MaintenanceResult:
    result = MaintenanceResult()
    path = handoff_dir / "work-log.md"
    if not path.exists():
        result.unresolved.append(".agent-handoff/work-log.md is missing.")
        return result

    original = read_text(path)
    sections = dated_h2_sections(original)
    if byte_count(original) <= WORK_LOG_MAX_BYTES and len(sections) <= WORK_LOG_MAX_SECTIONS:
        return result
    if len(sections) < 2:
        result.unresolved.append(
            "work-log.md exceeds its limit but has fewer than two complete dated sections to rotate."
        )
        return result

    remove_count = max(0, len(sections) - WORK_LOG_MAX_SECTIONS)
    while remove_count < len(sections) - 1:
        candidate = remove_spans(original, [(start, end) for start, end, _ in sections[:remove_count]])
        if byte_count(candidate) <= WORK_LOG_MAX_BYTES:
            break
        remove_count += 1

    if remove_count == 0:
        remove_count = 1
    removed_sections = sections[:remove_count]
    compacted = remove_spans(original, [(start, end) for start, end, _ in removed_sections])
    if byte_count(compacted) > WORK_LOG_MAX_BYTES:
        result.unresolved.append(
            "work-log.md still exceeds 64 KiB after preserving its newest complete dated section."
        )
        return result

    archived = "".join(section for _, _, section in removed_sections).strip() + "\n"
    reason = f"work log exceeded 64 KiB or {WORK_LOG_MAX_SECTIONS} dated sections"
    archive_content(handoff_dir, "work-log", archived, reason)
    atomic_write(path, compacted.lstrip("\n"))
    result.changed.extend([".agent-handoff/work-log.md", ".agent-handoff/archive.md"])
    result.warnings.append(f"Rotated {remove_count} old work-log section(s).")
    return result


def validation_table(text: str) -> tuple[list[str], int, int, list[str]] | None:
    lines = text.splitlines(keepends=True)
    separator_pattern = re.compile(r"^\s*\|(?:\s*:?-+:?\s*\|)+\s*$")
    for separator_index, line in enumerate(lines):
        if separator_index == 0 or not separator_pattern.match(line.rstrip("\r\n")):
            continue
        if not lines[separator_index - 1].lstrip().startswith("|"):
            continue
        data_start = separator_index + 1
        data_end = data_start
        while data_end < len(lines) and lines[data_end].lstrip().startswith("|"):
            data_end += 1
        return lines, data_start, data_end, lines[data_start:data_end]
    return None


def maintain_validation(handoff_dir: Path) -> MaintenanceResult:
    result = MaintenanceResult()
    path = handoff_dir / "validation.md"
    if not path.exists():
        result.unresolved.append(".agent-handoff/validation.md is missing.")
        return result

    original = read_text(path)
    parsed = validation_table(original)
    row_count = len(parsed[3]) if parsed else 0
    if byte_count(original) <= VALIDATION_MAX_BYTES and row_count <= VALIDATION_MAX_ROWS:
        return result
    if parsed is None or row_count < 2:
        result.unresolved.append(
            "validation.md exceeds its limit but has no safely rotatable Markdown table rows."
        )
        return result

    lines, data_start, data_end, rows = parsed
    remove_count = max(0, len(rows) - VALIDATION_MAX_ROWS)
    while remove_count < len(rows) - 1:
        candidate = "".join(lines[:data_start] + rows[remove_count:] + lines[data_end:])
        if byte_count(candidate) <= VALIDATION_MAX_BYTES:
            break
        remove_count += 1
    if remove_count == 0:
        remove_count = 1

    compacted = "".join(lines[:data_start] + rows[remove_count:] + lines[data_end:])
    if byte_count(compacted) > VALIDATION_MAX_BYTES:
        result.unresolved.append(
            "validation.md still exceeds 64 KiB after preserving its newest complete table row."
        )
        return result

    table_header = "".join(lines[data_start - 2:data_start])
    archived = table_header + "".join(rows[:remove_count])
    reason = f"validation history exceeded 64 KiB or {VALIDATION_MAX_ROWS} rows"
    archive_content(handoff_dir, "validation", archived, reason)
    atomic_write(path, compacted)
    result.changed.extend([".agent-handoff/validation.md", ".agent-handoff/archive.md"])
    result.warnings.append(f"Rotated {remove_count} old validation row(s).")
    return result


def completed_backlog_spans(text: str) -> list[tuple[int, int, str]]:
    lines = text.splitlines(keepends=True)
    offsets: list[int] = []
    cursor = 0
    for line in lines:
        offsets.append(cursor)
        cursor += len(line)

    spans: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        if not re.match(r"^- \[[xX]\] .+", line):
            continue
        end_index = index + 1
        while end_index < len(lines):
            candidate = lines[end_index]
            if not candidate.strip() or candidate.startswith((" ", "\t")):
                end_index += 1
                continue
            break
        start = offsets[index]
        end = offsets[end_index] if end_index < len(lines) else len(text)
        spans.append((start, end, text[start:end]))
    return spans


def maintain_backlog(handoff_dir: Path) -> MaintenanceResult:
    result = MaintenanceResult()
    path = handoff_dir / "backlog.md"
    if not path.exists():
        result.unresolved.append(".agent-handoff/backlog.md is missing.")
        return result

    original = read_text(path)
    if byte_count(original) <= CURRENT_STATE_MAX_BYTES:
        return result
    completed = completed_backlog_spans(original)
    if not completed:
        result.unresolved.append(
            "backlog.md exceeds 32 KiB and has no completed checklist items that can be archived mechanically."
        )
        return result

    remove_count = 0
    compacted = original
    while byte_count(compacted) > CURRENT_STATE_MAX_BYTES and remove_count < len(completed):
        remove_count += 1
        compacted = remove_spans(
            original,
            [(start, end) for start, end, _ in completed[:remove_count]],
        )
    if byte_count(compacted) > CURRENT_STATE_MAX_BYTES:
        result.unresolved.append(
            "backlog.md still exceeds 32 KiB after all completed checklist items were selected; original content was preserved."
        )
        return result

    archived = "".join(item for _, _, item in completed[:remove_count]).strip() + "\n"
    archive_content(
        handoff_dir,
        "backlog-completed",
        archived,
        "backlog exceeded 32 KiB; archived completed checklist items",
    )
    atomic_write(path, compacted)
    result.changed.extend([".agent-handoff/backlog.md", ".agent-handoff/archive.md"])
    result.warnings.append(f"Archived {remove_count} completed backlog item(s).")
    return result


def inspect_repository(repo: Path) -> MaintenanceResult:
    result = MaintenanceResult()
    handoff_path = repo / "AGENT_HANDOFF.md"
    handoff_dir = repo / ".agent-handoff"
    if not handoff_path.exists():
        result.unresolved.append("AGENT_HANDOFF.md is missing.")
        return result

    if not handoff_dir.is_dir():
        content = read_text(handoff_path)
        if byte_count(content) > SINGLE_HARD_BYTES:
            result.unresolved.append(
                f"Single-document AGENT_HANDOFF.md exceeds the 64 KiB hard limit ({byte_count(content)} bytes); migrate to multi layout."
            )
        elif byte_count(content) > SINGLE_SOFT_BYTES:
            result.warnings.append(
                f"Single-document AGENT_HANDOFF.md exceeds the 32 KiB soft limit ({byte_count(content)} bytes)."
            )
        return result

    for name in [
        "workspace.md",
        "decisions.md",
        "work-log.md",
        "validation.md",
        "backlog.md",
        "risks.md",
        "archive.md",
    ]:
        if not (handoff_dir / name).exists():
            result.unresolved.append(f".agent-handoff/{name} is missing.")

    snapshot_path = handoff_dir / "snapshot.md"
    if snapshot_path.exists():
        snapshot = read_text(snapshot_path)
        metrics = f"{byte_count(snapshot)} bytes, {line_count(snapshot)} lines"
        if exceeds_snapshot_hard_limit(snapshot):
            result.unresolved.append(
                f"snapshot.md exceeds the 32 KiB / 400 line hard limit ({metrics})."
            )
        elif exceeds_snapshot_soft_limit(snapshot):
            result.warnings.append(
                f"snapshot.md exceeds the 16 KiB / 240 line soft limit ({metrics})."
            )
    else:
        result.unresolved.append(".agent-handoff/snapshot.md is missing.")

    work_log_path = handoff_dir / "work-log.md"
    if work_log_path.exists():
        work_log = read_text(work_log_path)
        sections = len(dated_h2_sections(work_log))
        if byte_count(work_log) > WORK_LOG_MAX_BYTES or sections > WORK_LOG_MAX_SECTIONS:
            result.warnings.append(
                f"work-log.md exceeds 64 KiB or {WORK_LOG_MAX_SECTIONS} dated sections ({byte_count(work_log)} bytes, {sections} sections)."
            )

    validation_path = handoff_dir / "validation.md"
    if validation_path.exists():
        validation = read_text(validation_path)
        parsed = validation_table(validation)
        rows = len(parsed[3]) if parsed else 0
        if byte_count(validation) > VALIDATION_MAX_BYTES or rows > VALIDATION_MAX_ROWS:
            result.warnings.append(
                f"validation.md exceeds 64 KiB or {VALIDATION_MAX_ROWS} rows ({byte_count(validation)} bytes, {rows} rows)."
            )

    for name in ["backlog.md", "risks.md"]:
        path = handoff_dir / name
        if path.exists() and path.stat().st_size > CURRENT_STATE_MAX_BYTES:
            result.unresolved.append(
                f"{name} exceeds the 32 KiB current-state limit ({path.stat().st_size} bytes); semantic cleanup is required."
            )

    archive_dir = handoff_dir / "archive"
    if archive_dir.is_dir():
        for path in archive_dir.glob("*.md"):
            if path.stat().st_size > ARCHIVE_CHUNK_BYTES:
                result.unresolved.append(
                    f"Archive chunk {path.name} exceeds the 128 KiB limit ({path.stat().st_size} bytes)."
                )
    return result


def deduplicate_result(result: MaintenanceResult) -> MaintenanceResult:
    result.changed = list(dict.fromkeys(result.changed))
    result.warnings = list(dict.fromkeys(result.warnings))
    result.unresolved = list(dict.fromkeys(result.unresolved))
    return result


def maintain_repository(
    repo: Path, include_snapshot: bool = True, include_logs: bool = True
) -> MaintenanceResult:
    repo = repo.expanduser().resolve()
    handoff_dir = repo / ".agent-handoff"
    result = MaintenanceResult()
    if not handoff_dir.is_dir():
        return inspect_repository(repo)

    if include_snapshot:
        result.merge(maintain_snapshot(handoff_dir))
    if include_logs:
        result.merge(maintain_work_log(handoff_dir))
        result.merge(maintain_validation(handoff_dir))
        result.merge(maintain_backlog(handoff_dir))
    result.merge(inspect_repository(repo))
    return deduplicate_result(result)


def print_result(result: MaintenanceResult) -> None:
    print(
        "Handoff maintenance: "
        f"changed={len(result.changed)} warnings={len(result.warnings)} unresolved={len(result.unresolved)}"
    )
    for path in result.changed:
        print(f"CHANGED: {path}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for unresolved in result.unresolved:
        print(f"UNRESOLVED: {unresolved}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check, compact, and rotate repository-local Agent handoff state."
    )
    parser.add_argument("--repo", default=".", help="Repository root. Defaults to the current directory.")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--check", action="store_true", help="Inspect limits without writing files (default).")
    actions.add_argument(
        "--compact-if-needed",
        action="store_true",
        help="Compact an oversized snapshot and rotate oversized history safely.",
    )
    actions.add_argument(
        "--rotate",
        action="store_true",
        help="Rotate oversized work-log, validation, and completed backlog records only.",
    )
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_dir():
        parser.error(f"repository path is not a directory: {repo}")

    if args.compact_if_needed:
        result = maintain_repository(repo, include_snapshot=True, include_logs=True)
    elif args.rotate:
        result = maintain_repository(repo, include_snapshot=False, include_logs=True)
    else:
        result = inspect_repository(repo)
    print_result(result)
    return 2 if result.unresolved else 0


if __name__ == "__main__":
    raise SystemExit(main())
