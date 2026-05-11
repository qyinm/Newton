from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class BugDraftError(ValueError):
    """Raised when a tracker cannot produce a bug ticket draft."""


@dataclass(frozen=True)
class FailedTrackerItem:
    item: str
    env: str
    status: str
    notes: str


def write_bug_ticket_draft(tracker_path: Path, output_path: Path | None = None) -> Path:
    if not tracker_path.exists():
        raise BugDraftError(f"qa run tracker not found: {tracker_path}")

    failed_item = _first_failed_tracker_item(tracker_path.read_text())
    if failed_item is None:
        raise BugDraftError("no failed tracker item found")

    output_path = output_path or tracker_path.parent / "bug-ticket-draft.md"
    output_path.write_text(_render_bug_ticket_draft(failed_item, tracker_path))
    return output_path


def _first_failed_tracker_item(markdown: str) -> FailedTrackerItem | None:
    current_item: str | None = None
    current_env = "dev"
    current_envs: dict[str, dict[str, str]] = {"dev": {"status": "not run", "notes": ""}}

    def flush() -> FailedTrackerItem | None:
        if current_item is None:
            return None
        for env, state in current_envs.items():
            if state["status"].strip().lower() == "failed":
                return FailedTrackerItem(
                    item=current_item,
                    env=env.strip() or "dev",
                    status="failed",
                    notes=state["notes"].strip(),
                )
        return None

    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- [ ] ", "- [x] ", "- [X] ")):
            failed = flush()
            if failed is not None:
                return failed
            current_item = _tracker_item_text(stripped)
            current_env = "dev"
            current_envs = {"dev": {"status": "not run", "notes": ""}}
            continue
        if current_item is None:
            continue
        env_heading = _environment_heading(stripped)
        if env_heading is not None:
            current_env = env_heading
            current_envs.setdefault(current_env, {"status": "not run", "notes": ""})
            continue
        if stripped.startswith("- env:"):
            current_env = stripped.removeprefix("- env:").strip()
            current_envs.setdefault(current_env, {"status": "not run", "notes": ""})
        elif stripped.startswith("- status:"):
            current_envs.setdefault(current_env, {"status": "not run", "notes": ""})["status"] = (
                stripped.removeprefix("- status:").strip()
            )
        elif stripped.startswith("- notes:"):
            current_envs.setdefault(current_env, {"status": "not run", "notes": ""})["notes"] = (
                stripped.removeprefix("- notes:").strip()
            )

    return flush()


def _environment_heading(stripped: str) -> str | None:
    for env in ("dev", "stg", "prod"):
        if stripped == f"- {env}:":
            return env
    return None


def _tracker_item_text(stripped_line: str) -> str:
    for prefix in ("- [ ] ", "- [x] ", "- [X] "):
        if stripped_line.startswith(prefix):
            return stripped_line.removeprefix(prefix).strip()
    return stripped_line


def _render_bug_ticket_draft(item: FailedTrackerItem, tracker_path: Path) -> str:
    notes = item.notes or "TBD"
    return f"""# Bug Ticket Draft: {item.item}

## Summary

{item.item} fails in {item.env}.

## Failed Checklist Item

- Item: {item.item}
- Environment: {item.env}
- Status: {item.status}
- Notes: {notes}

## Reproduction Steps

1. Open the environment under test.
2. Execute the failed checklist item: {item.item}
3. Record the actual result and attach evidence if available.

## Expected Result

The checklist item should pass.

## Actual Result

{notes}

## Source

- Tracker: `{tracker_path}`
"""
