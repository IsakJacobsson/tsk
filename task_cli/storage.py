"""Read/write tasks to disk."""

import json
from pathlib import Path

from task_cli.models import Task

STORAGE_DIR = Path.home() / ".tsk"
STORAGE_FILE = STORAGE_DIR / "tasks.json"


def ensure_storage() -> None:
    """Create the storage directory and file if they don't exist."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    if not STORAGE_FILE.exists():
        STORAGE_FILE.write_text("[]")


def load_tasks() -> list[Task]:
    """Read and deserialize all tasks from disk."""
    ensure_storage()
    data = json.loads(STORAGE_FILE.read_text())
    return [Task.from_dict(item) for item in data]


def save_tasks(tasks: list[Task]) -> None:
    """Serialize and write all tasks to disk."""
    ensure_storage()
    data = [task.to_dict() for task in tasks]
    STORAGE_FILE.write_text(json.dumps(data, indent=2))


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
