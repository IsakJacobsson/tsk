---
applyTo: '**'
---

# Copilot instructions

## Project Overview

`tsk` is a personal command-line task manager written in Python. Tasks are persisted as a human-readable Markdown file at `~/.tsk/tasks.md`. The tool is installed globally and invoked as `tsk`.

## Specification-Driven Development

**This is a specification-driven repository. No code changes may be made without first updating `spec.md`.**

The workflow for any change is:

1. **Update `spec.md` first.** Describe the desired behaviour, data model change, new command, or bug fix in the specification. The spec is the source of truth.
2. **Review the spec change.** Ensure the spec is clear, complete, and consistent with the rest of the document before touching any source file.
3. **Implement the code.** Write or modify source files to match exactly what the updated spec describes. The implementation must not diverge from the spec.

If you are asked to add a feature, fix a bug, or refactor code, start by editing `spec.md`. Do not write a single line of implementation code until the spec reflects the intended state.

## Repository Structure

```
task-cli/
├── pyproject.toml        # Package metadata, dependencies, entry point
├── README.md
├── spec.md               # Single source of truth — update this first
├── AGENTS.md             # This file
└── task_cli/
    ├── __init__.py       # Empty package marker
    ├── cli.py            # CLI command definitions (entry point: main)
    ├── models.py         # Task data model and TaskStatus enum
    └── storage.py        # Markdown persistence layer (~/.tsk/tasks.md)
```

## Key Files

| File | Purpose |
|------|---------|
| `spec.md` | Full behavioural specification. **Edit this before anything else.** |
| `task_cli/cli.py` | `click`-based CLI commands (`add`, `list`, `done`, `wontdo`, `delete`) |
| `task_cli/models.py` | `Task` dataclass and `TaskStatus` enum |
| `task_cli/storage.py` | Reading/writing `~/.tsk/tasks.md`; ID collision handling |
| `pyproject.toml` | Build config; entry point `tsk = "task_cli.cli:main"` |

## Installation

```bash
pipx install .
```

This makes `tsk` available globally.

## Running the Tool

```bash
tsk add "Buy groceries"
tsk list
tsk list --all
tsk done a3f8c01
tsk wontdo e1b9d44
tsk delete a3f8c01 --yes
```

## Testing

To run the tests, simply run:

```bash
tox
```

## Coding Guidelines

- Follow the data model and file format defined in `spec.md` exactly.
- Do not introduce new dependencies without updating both `spec.md` and `pyproject.toml`.
- Keep storage human-readable; the Markdown format in `~/.tsk/tasks.md` is intentional.
- All commands accept full or unambiguous partial task IDs (prefix matching).
- Python >= 3.10 is required; use modern type hint syntax (`str | None`, etc.).
