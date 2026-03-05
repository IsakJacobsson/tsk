# Specification: `tsk` — CLI Task Manager

## 1. Overview

`tsk` is a personal command-line task manager written in Python. Tasks are persisted as a human-readable Markdown file on disk. The tool is meant to be installed globally and invoked as `tsk` from any directory.

## 2. Project Structure

```
task-cli/
├── pyproject.toml          # Package metadata, dependencies, entry point
├── README.md
├── spec.md                 # This file
├── task_cli/
│   ├── __init__.py         # Empty package marker
│   ├── cli.py              # CLI command definitions (entry point: main)
│   ├── models.py           # Task data model and TaskStatus enum
│   └── storage.py          # Markdown persistence layer
```

---

## 3. Installation

### Build system

Uses `setuptools` (>= 68.0) via `pyproject.toml`.

### Package metadata

| Field            | Value                        |
|------------------|------------------------------|
| Name             | `task-cli`                   |
| Version          | `0.1.0`                      |
| Description      | A simple CLI task manager    |
| Python version   | `>= 3.10`                    |
| Dependencies     | `click >= 8.0`               |

### Entry point

```toml
[project.scripts]
tsk = "task_cli.cli:main"
```

Running `pipx install .` makes the `tsk` command available globally.

---

## 4. Data Model (`task_cli/models.py`)

### 4.1 `TaskStatus` Enum

```python
class TaskStatus(str, Enum):
    OPEN   = "open"
    DONE   = "done"
    WONTDO = "wontdo"
```

- Inherits from both `str` and `Enum` so values can be compared directly to strings.
- `OPEN` is the default state for a newly created task.
- `DONE` means the task was completed.
- `WONTDO` means the task was intentionally abandoned.

### 4.2 `Task` Dataclass

```python
@dataclass
class Task:
    message:    str
    id:         str = ""
    created_at: str = ""
    status:     TaskStatus = TaskStatus.OPEN
```

**Field details:**

| Field        | Type          | Description                                               |
|--------------|---------------|-----------------------------------------------------------|
| `message`    | `str`         | Human-readable task description. Required.               |
| `id`         | `str`         | 7-character hex ID (auto-generated if empty).            |
| `created_at` | `str`         | ISO 8601 datetime string (auto-set to `now()` if empty). |
| `status`     | `TaskStatus`  | Current task state. Defaults to `OPEN`.                  |

**`__post_init__` logic:**

1. If `created_at` is empty, it is set to `datetime.now().isoformat()`.
2. If `id` is empty, it is generated via `generate_id(message, created_at)`.
3. If `status` is not already a `TaskStatus` instance, it is coerced from a string (case-insensitive, stripped). Falls back to `OPEN` on invalid input.

**Compatibility property:**

- `task.completed` → `bool` property that returns `True` when `status == DONE`.
- Setting `task.completed = True` sets `status = DONE`; `False` sets `status = OPEN`.  
  (Retained for backwards compatibility with any code predating the three-state status model.)

**Serialisation helpers:**

- `task.to_dict()` — returns a plain `dict` with `status` serialized as its string value.
- `Task.from_dict(data)` — constructs a `Task` from a `dict`. Handles both the modern `status` field and the legacy `completed` boolean. Invalid or missing status values default to `OPEN`.

### 4.3 `generate_id(message, created_at)`

```python
def generate_id(message: str, created_at: datetime) -> str:
    raw = f"{created_at.isoformat()}:{message}"
    return hashlib.sha256(raw.encode()).hexdigest()[:7]
```

- Produces a **7-character lowercase hex string** derived from the SHA-256 hash of `"<iso-timestamp>:<message>"`.
- Effectively collision-free for personal task volumes.
- Collisions are handled at the storage layer (see §5.3).
- Example: `a3f8c01`

---

## 5. Storage (`task_cli/storage.py`)

### 5.1 Storage Location

| Path               | Value                   |
|--------------------|-------------------------|
| Directory          | `~/.tsk/`               |
| File               | `~/.tsk/tasks.md`       |

`ensure_storage()` creates the directory (recursively) and the file (with a `# Tasks\n\n` header) if either does not exist.

### 5.2 File Format

Tasks are stored as a Markdown file grouped under day headings:

```markdown
# Tasks

## Monday 2026-03-02

- [ ] Buy groceries
  id: a3f8c01
  created_at: 2026-03-02T10:30:00.000000
  status: open

- [x] Call the plumber
  id: b7c2e90
  created_at: 2026-03-02T08:00:00.000000
  status: done

## Sunday 2026-03-01

- [-] Fix the doorbell
  id: e1b9d44
  created_at: 2026-03-01T11:15:00.000000
  status: wontdo
```

**Heading format:** `## <Weekday> <YYYY-MM-DD>` (e.g. `## Monday 2026-03-02`).  
Tasks whose `created_at` cannot be parsed are placed under `## Unknown` at the end.

**Checkbox markers:**

| Marker | Status  |
|--------|---------|
| `[ ]`  | `open`  |
| `[x]`  | `done`  |
| `[-]`  | `wontdo`|

Each task entry consists of the checkbox line followed by indented (two-space) metadata lines:
- `  id: <7-char-hex>`
- `  created_at: <iso-datetime>`
- `  status: <open|done|wontdo>`

A blank line separates consecutive task entries.

### 5.3 Storage Functions

#### `ensure_storage() -> None`
Creates `~/.tsk/` and initialises `tasks.md` with `# Tasks\n\n` if necessary.

#### `load_tasks() -> list[Task]`
Reads `tasks.md` line by line and reconstructs `Task` objects.

- Calls `ensure_storage()` first.
- Scans for lines matching `- [( |x|-)] <message>`.
- Reads subsequent lines that start with two spaces as metadata keys (`id:`, `created_at:`, `status:`).
- Constructs each `Task` via `Task.from_dict(...)`.
- Returns tasks in file order (top-to-bottom).

#### `save_tasks(tasks: list[Task]) -> None`
Serialises and overwrites `tasks.md`.

- Groups tasks by `YYYY-MM-DD` date (from `created_at`).
- Sorts groups chronologically; `unknown` group appended last.
- Writes a `## <Weekday> <YYYY-MM-DD>` heading per group.
- Writes each task as described in §5.2.

#### `add_task(task: Task) -> None`
Appends a task and persists.

- Loads existing tasks and collects their IDs.
- If the new task's ID collides, regenerates it by appending an incrementing nonce to the message before hashing: `generate_id(message + str(nonce), created_at)`.
- Appends the task and calls `save_tasks`.

#### `find_task_by_id(partial_id: str) -> Task | None`
Returns a task whose `id` starts with `partial_id`, or `None` if zero or multiple matches.

#### `complete_task(partial_id: str) -> Task | None`
Sets `status = DONE` on the uniquely matched task, saves, and returns it. Returns `None` if not found or ambiguous.

#### `wont_do_task(partial_id: str) -> Task | None`
Sets `status = WONTDO` on the uniquely matched task, saves, and returns it. Returns `None` if not found or ambiguous.

#### `delete_task(partial_id: str) -> Task | None`
Removes the uniquely matched task from the list, saves, and returns the deleted task. Returns `None` if not found or ambiguous.

---

## 6. CLI (`task_cli/cli.py`)

Entry point callable: `task_cli.cli:main` (a `click.Group`).

```
tsk [COMMAND] [OPTIONS] [ARGS]
```

### Global options

- All commands support the standard help option: `--help`.
- A short form `-h` is also supported for convenience: `-h`, `--help`.

### 6.1 Command Reference

#### `tsk add <message>`

Creates a new task with `status = open`.

```
$ tsk add "Buy groceries"
Added task [a3f8c01] Buy groceries
```

- `message` — positional argument, the task description.
- Calls `add_task(task)` which handles ID collision.

---

#### `tsk list [--all]`

Displays tasks sorted by `created_at`, grouped by date.

```
$ tsk list
2026-03-02
  [ ] a3f8c01  Buy groceries

2026-03-01
  [ ] b7c2e90  Call the dentist
```

- Without `--all`: only `open` tasks are shown.
- With `--all`: all tasks (open, done, wontdo) are shown.
- Each row: `  <status> <id>  <message>`
- Groups are separated by a blank line.
- Prints `No tasks.` if the filtered list is empty.

**Status indicators in list output:**

| Output | Status  |
|--------|---------|
| `[ ]`  | `open`  |
| `[x]`  | `done`  |
| `[-]`  | `wontdo`|

**Option:**

| Flag    | Description                              |
|---------|------------------------------------------|
| `--all`, `-a` | Show all tasks including done and won't-do. |

---

#### `tsk done <task_id>`

Marks a task as `done`.

```
$ tsk done a3f8c01
Completed: Buy groceries

$ tsk done xyz
No unique task found matching 'xyz'.
```

- `task_id` — full or unambiguous partial ID.
- Delegates to `complete_task(task_id)`.
- Prints an error message if no unique match is found.

---

#### `tsk wontdo <task_id>`

Marks a task as `wontdo`.

```
$ tsk wontdo e1b9d44
Marked won't-do: Fix the doorbell

$ tsk wontdo xyz
No unique task found matching 'xyz'.
```

- `task_id` — full or unambiguous partial ID.
- Delegates to `wont_do_task(task_id)`.
- Prints an error message if no unique match is found.

---

#### `tsk delete <task_id> [--yes]`

Deletes a task after optional confirmation.

```
$ tsk delete a3f8c01
Delete task [a3f8c01] Buy groceries? [y/N]: y
Deleted: Buy groceries

$ tsk delete a3f8c01 --yes
Deleted: Buy groceries
```

- `task_id` — full or unambiguous partial ID.
- Prompts for confirmation unless `--yes` / `-y` is passed.
- Uses `find_task_by_id` to resolve the task before prompting, then calls `delete_task`.
- Prints an error message if no unique match is found.
- Prints `Aborted.` if the confirmation prompt is declined.

**Options:**

| Flag         | Alias | Description                      |
|--------------|-------|----------------------------------|
| `--yes`      | `-y`  | Skip confirmation prompt.        |

---

#### `tsk edit <task_id> <message>`

Edit the text of an existing task without changing its `id`, `created_at`, or `status`.

```
$ tsk edit a3f8c01 "Buy tomatoes"
Updated: Buy tomatoes
```

- `task_id` — full or unambiguous partial ID.
- `message` — the new description for the task.
- The command delegates to `storage.edit_task(partial_id, new_message)`.
- If no unique match is found, prints the same error used by other commands:
  `No unique task found matching '<id>'.`

---

## 7. Partial ID Matching

All commands that accept a `<task_id>` support **prefix matching**:

- Any prefix of a task's full 7-character ID is accepted.
- If the prefix matches exactly **one** task, the operation proceeds.
- If the prefix matches **zero** or **more than one** task, the operation is aborted and an error is printed.

Example: if the only task starting with `a3f` is `a3f8c01`, then `tsk done a3f` works.

---

## 8. Error Handling

| Scenario                          | Behaviour                                          |
|-----------------------------------|----------------------------------------------------|
| No match for partial ID           | Prints `No unique task found matching '<id>'.`     |
| Ambiguous partial ID              | Same message (returns `None` from storage layer)   |
| Confirmation declined on delete   | Prints `Aborted.`                                  |
| `delete_task` fails after confirm | Prints `Failed to delete task.`                    |
| Unparseable `created_at`          | Task placed under `## Unknown` group in file       |
| Invalid `status` value on load    | Defaults to `TaskStatus.OPEN`                      |
| ID collision on add               | Nonce appended, ID regenerated automatically       |

---

## 9. Dependencies

| Package    | Version   | Purpose             |
|------------|-----------|---------------------|
| `click`    | `>= 8.0`  | CLI framework       |
| Python     | `>= 3.10` | Runtime (uses `match`-compatible type hints, `str | None`, etc.) |

---

## 10. Testing

### 10.1 Framework

Tests are written with **`pytest`** and live in a top-level `tests/` directory:

```
tests/
├── conftest.py       # Shared fixtures: storage isolation
├── test_models.py    # Unit tests for models.py
├── test_storage.py   # Unit tests for storage.py
└── test_cli.py       # Integration tests for cli.py via Click's CliRunner
```

`pytest` is listed under `[project.optional-dependencies]` in `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0"]
```

Tests are run through **`tox`**, which manages an isolated virtual environment automatically. A `tox.ini` file at the repository root defines the test environment.

Run all tests with: `tox`.  
To run without tox: `pip install -e ".[dev]"` then `pytest`.

### 10.1a Tox Configuration (`tox.ini`)

```ini
[tox]
envlist = py

[testenv]
commands = pytest
```

- `extras = dev` installs the package together with the `[dev]` optional dependencies (pytest) into the isolated tox virtualenv.
- `{posargs}` allows passing extra arguments to pytest (e.g. `tox -- -k test_add`).
- `tox` is **not** listed as a project dependency; it is a developer tool installed separately (`pip install tox` or `pipx install tox`).

### 10.2 Storage Isolation

All tests that touch the storage layer must **not** read or write `~/.tsk/tasks.md`. Isolation is achieved by patching the module-level constants in `task_cli.storage` using `monkeypatch`:

```python
@pytest.fixture
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setattr("task_cli.storage.STORAGE_DIR", tmp_path)
    monkeypatch.setattr("task_cli.storage.STORAGE_FILE", tmp_path / "tasks.md")
```

This fixture must be used (directly or via `autouse`) in every test that invokes storage functions or CLI commands.

### 10.3 CLI Testing

CLI commands are tested via Click's `CliRunner`, which invokes commands in-process without spawning a subprocess:

```python
from click.testing import CliRunner
from task_cli.cli import main

def test_add_command(isolated_storage):
    runner = CliRunner()
    result = runner.invoke(main, ["add", "Buy groceries"])
    assert result.exit_code == 0
    assert "Added task" in result.output
```

### 10.4 Test Coverage Areas

| Module        | What to test                                                              |
|---------------|---------------------------------------------------------------------------|
| `models.py`   | `generate_id` determinism; `Task.__post_init__` auto-fill; status coercion; `completed` property; `to_dict` / `from_dict` round-trip |
| `storage.py`  | `load_tasks` parses all status markers; `save_tasks` round-trip; `add_task` ID collision handling; `find_task_by_id` prefix matching; `complete_task`, `wont_do_task`, `delete_task` mutations |
| `cli.py`      | Each command's happy path and error path (no match, ambiguous ID, delete confirmation) |
