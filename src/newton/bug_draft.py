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
    current_status = "not run"
    current_notes = ""

    def flush() -> FailedTrackerItem | None:
        if current_item is None:
            return None
        if current_status.strip().lower() == "failed":
            return FailedTrackerItem(
                item=current_item,
                env=current_env.strip() or "dev",
                status="failed",
                notes=current_notes.strip(),
            )
        return None

    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("- [ ] "):
            failed = flush()
            if failed is not None:
                return failed
            current_item = stripped.removeprefix("- [ ] ").strip()
            current_env = "dev"
            current_status = "not run"
            current_notes = ""
            continue
        if current_item is None:
            continue
        if stripped.startswith("- env:"):
            current_env = stripped.removeprefix("- env:").strip()
        elif stripped.startswith("- status:"):
            current_status = stripped.removeprefix("- status:").strip()
        elif stripped.startswith("- notes:"):
            current_notes = stripped.removeprefix("- notes:").strip()

    return flush()


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
