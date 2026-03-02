"""Read/write tasks to disk as a human-readable Markdown file grouped by day."""

from pathlib import Path
import re
from collections import defaultdict
from datetime import datetime

from task_cli.models import Task

STORAGE_DIR = Path.home() / ".tsk"
STORAGE_FILE = STORAGE_DIR / "tasks.md"


def ensure_storage() -> None:
    """Create the storage directory and file if they don't exist."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    if not STORAGE_FILE.exists():
        STORAGE_FILE.write_text("# Tasks\n\n")


def load_tasks() -> list[Task]:
    """Read and parse all tasks from the Markdown file."""
    ensure_storage()
    text = STORAGE_FILE.read_text()
    lines = text.splitlines()
    tasks: list[Task] = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")
        if line.startswith("- ["):
            m = re.match(r"- \[( |x)\] (.*)", line)
            if m:
                completed = m.group(1) == "x"
                message = m.group(2).strip()
                id_ = ""
                created_at = ""
                i += 1
                # read subsequent indented metadata lines
                while i < len(lines) and lines[i].startswith("  "):
                    meta = lines[i].strip()
                    if meta.startswith("id:"):
                        id_ = meta[len("id:"):].strip()
                    elif meta.startswith("created_at:"):
                        created_at = meta[len("created_at:"):].strip()
                    i += 1
                tasks.append(
                    Task.from_dict(
                        {"message": message, "id": id_, "created_at": created_at, "completed": completed}
                    )
                )
                continue
        i += 1
    return tasks


def save_tasks(tasks: list[Task]) -> None:
    """Write all tasks to the Markdown file grouped under day headings.

    Headings are formatted as `## Weekday YYYY-MM-DD` (e.g. `## Monday 2026-03-02`).
    """
    ensure_storage()
    # Group tasks by date (YYYY-MM-DD)
    groups: dict[str, list[Task]] = defaultdict(list)
    for t in tasks:
        try:
            dt = datetime.fromisoformat(t.created_at)
            key = dt.date().isoformat()
        except Exception:
            key = "unknown"
        groups[key].append(t)

    parts: list[str] = ["# Tasks", ""]
    # sort keys; put unknown at the end
    keys = sorted(k for k in groups.keys() if k != "unknown")
    if "unknown" in groups:
        keys.append("unknown")

    for key in keys:
        if key == "unknown":
            heading = "## Unknown"
        else:
            weekday = datetime.fromisoformat(key).strftime("%A")
            heading = f"## {weekday} {key}"
        parts.append(heading)
        parts.append("")
        for t in groups[key]:
            mark = "x" if t.completed else " "
            parts.append(f"- [{mark}] {t.message}")
            parts.append(f"  id: {t.id}")
            parts.append(f"  created_at: {t.created_at}")
            parts.append("")

    STORAGE_FILE.write_text("\n".join(parts))


def add_task(task: Task) -> None:
    """Append a single task and persist. Handle ID collisions."""
    tasks = load_tasks()
    existing_ids = {t.id for t in tasks}
    # Handle collision by appending a nonce
    nonce = 0
    while task.id in existing_ids:
        nonce += 1
        from task_cli.models import generate_id
        from datetime import datetime

        task.id = generate_id(task.message + str(nonce), datetime.fromisoformat(task.created_at))
    tasks.append(task)
    save_tasks(tasks)


def find_task_by_id(partial_id: str) -> Task | None:
    """Find a task by full or partial ID. Returns None if ambiguous or not found."""
    tasks = load_tasks()
    matches = [t for t in tasks if t.id.startswith(partial_id)]
    if len(matches) == 1:
        return matches[0]
    return None


def complete_task(partial_id: str) -> Task | None:
    """Mark a task as completed by full or partial ID."""
    tasks = load_tasks()
    matches = [t for t in tasks if t.id.startswith(partial_id)]
    if len(matches) == 1:
        matches[0].completed = True
        save_tasks(tasks)
        return matches[0]
    return None


def delete_task(partial_id: str) -> Task | None:
    """Delete a task by full or partial ID and persist changes.

    Returns the deleted Task when exactly one match is found, otherwise None.
    """
    tasks = load_tasks()
    matches = [t for t in tasks if t.id.startswith(partial_id)]
    if len(matches) == 1:
        to_delete = matches[0]
        tasks = [t for t in tasks if t.id != to_delete.id]
        save_tasks(tasks)
        return to_delete
    return None
