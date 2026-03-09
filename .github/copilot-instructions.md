# Copilot instructions

## Project Overview

`tsk` is a personal command-line task manager written in Python. Tasks are persisted as a human-readable Markdown file at `~/.tsk/tasks.md`. The tool is installed globally and invoked as `tsk`.

## Agent development guidelines

### Key rules

- **Specification-driven repository.** No code changes may be made without first updating `spec.md`. The specification is the single source of truth for all behaviour, data models, and file formats. All implementation must strictly follow the spec.
- **Test driven development.** Tests must be written based on the updated spec before any implementation. Tests must fail before implementation and pass after. No feature or fix may be written without corresponding test cases.

### Development workflow

1. **Update `spec.md` first.** Describe the desired behaviour, data model change, new command, or bug fix in the specification. The spec is the source of truth.
2. **Review the spec change.** Pause here and let the developer or team review the updated spec to ensure it accurately captures the intended change and is clear and unambiguous.
3. **Write test cases.** Based on the updated spec, write test cases that validate the new behaviour or fix. These tests should fail before implementation. See [Testing](#testing) for details on the testing framework and guidelines.
4. **Implement the code.** Write or modify source files to match exactly what the updated spec describes. The implementation must not diverge from the spec.
5. **Run tests and ensure they pass.** All tests, including new ones, must pass before the change is considered complete. If tests fail, revisit the implementation and spec to identify discrepancies.

## Key Files

| File | Purpose |
|------|---------|
| `spec.md` | Full behavioural specification. **Edit this before anything else.** |
| `tests/` | Pytest tests for validating the behaviour described in `spec.md`. |
| `tox.ini` | Test configuration for running the test suite. The whole test suite should be run using just `tox`. |

## Testing

To run the tests, simply run:

```bash
tox
```