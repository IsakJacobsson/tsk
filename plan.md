# Plan: `tsk` — A Python CLI Task Manager

## 1. Project Structure

```
task-tool/
├── pyproject.toml          # Package metadata, dependencies, entry point
├── README.md
├── task_cli/
│   ├── __init__.py
│   ├── cli.py              # CLI commands (entry point)
│   ├── storage.py          # Read/write tasks to disk
│   └── models.py           # Task data model
```

## 2. Data Model (`models.py`)

- **Task** with fields:
  - `id` — short SHA hash (see below)
  - `message` — the task description (string)
  - `created_at` — datetime of creation (used for sorting)
  - `completed` — boolean, default `False`

### Task ID — Short SHA Hash

Each task gets a **7-character SHA-256 hash** derived from the creation timestamp + message content:

```python
import hashlib, datetime

def generate_id(message: str, created_at: datetime.datetime) -> str:
    raw = f"{created_at.isoformat()}:{message}"
    return hashlib.sha256(raw.encode()).hexdigest()[:7]
```

- Example ID: `a3f8c01`
- Git-inspired, short enough to type, virtually collision-free for a personal task list
- If a collision is detected on insert, regenerate with a nonce appended
- Users reference tasks by ID: `tsk done a3f8c01`
- Partial matching supported: typing `a3f` works as long as it's unambiguous

## 3. Storage (`storage.py`)

- Tasks stored as JSON in a file at `~/.tsk/tasks.json`
- Functions:
  - `load_tasks()` — read and deserialize all tasks from disk
  - `save_tasks(tasks)` — serialize and write all tasks to disk
  - `ensure_storage()` — create the directory/file if it doesn't exist

## 4. CLI Commands (`cli.py`)

Built with Python's `click` library for clean syntax. Base command: **`tsk`**.

| Command | Usage | Description |
|---|---|---|
| **add** | `tsk add "Buy groceries"` | Create a new task |
| **list** | `tsk list` | Show incomplete tasks (default) |
| | `tsk list --all` | Show all tasks (complete + incomplete) |
| **done** | `tsk done <id>` | Mark a task as complete |

### Usage Examples

```bash
# Add tasks
$ tsk add "Buy groceries"
✓ Added task [a3f8c01] Buy groceries

$ tsk add "Fix the doorbell"
✓ Added task [e1b9d44] Fix the doorbell

# List incomplete tasks (default)
$ tsk list
2026-03-02
  [ ] a3f8c01  Buy groceries          10:30
  [ ] e1b9d44  Fix the doorbell       11:15

# List all tasks including completed
$ tsk list --all
2026-03-02
  [x] b7c2e90  Call the plumber       08:00
  [ ] a3f8c01  Buy groceries          10:30
  [ ] e1b9d44  Fix the doorbell       11:15

# Mark a task done (full ID)
$ tsk done a3f8c01
✓ Completed: Buy groceries

# Mark a task done (partial ID — works if unambiguous)
$ tsk done e1b
✓ Completed: Fix the doorbell
```

## 5. Output Formatting

- Tasks grouped and sorted by creation date/time (newest last or first — TBD)
- Display format example:
  ```
  2026-03-02
    [ ] a3f8c01  Buy groceries          10:30
    [x] e1b9d44  Fix the doorbell       11:15

  2026-03-01
    [ ] b7c2e90  Call the dentist       09:00
  ```
- Incomplete tasks show `[ ]`, completed show `[x]`

## 6. Global Installation

- Define a console script entry point in `pyproject.toml`:
  ```toml
  [project.scripts]
  tsk = "task_cli.cli:main"
  ```
- Install globally with `pip install -e .` (or `pipx install .`)
- After install, `tsk` is available from any directory

## 7. Dependencies

- **click** — CLI framework
- **Python 3.10+** — standard library for `datetime`, `json`, `pathlib`

## 8. Implementation Order

1. Scaffold project (`pyproject.toml`, package directory)
2. Implement `models.py` (Task dataclass)
3. Implement `storage.py` (JSON persistence)
4. Implement `cli.py` (`add`, `list`, `done` commands)
5. Install with `pip install -e .` and test