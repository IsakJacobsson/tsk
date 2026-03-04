"""Shared pytest fixtures."""

import pytest


@pytest.fixture
def isolated_storage(tmp_path, monkeypatch):
    """Redirect all storage I/O to a temporary directory.

    Any test (or fixture) that touches task_cli.storage must use this fixture
    to avoid reading/writing the real ~/.tsk/tasks.md.
    """
    monkeypatch.setattr("task_cli.storage.STORAGE_DIR", tmp_path)
    monkeypatch.setattr("task_cli.storage.STORAGE_FILE", tmp_path / "tasks.md")
    return tmp_path
