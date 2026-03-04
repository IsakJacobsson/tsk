"""Unit tests for task_cli/models.py."""

from datetime import datetime

import pytest

from task_cli.models import Task, TaskStatus, generate_id


# ---------------------------------------------------------------------------
# generate_id
# ---------------------------------------------------------------------------

class TestGenerateId:
    def test_returns_seven_chars(self):
        dt = datetime(2026, 3, 2, 10, 30, 0)
        result = generate_id("Buy groceries", dt)
        assert len(result) == 7

    def test_deterministic(self):
        dt = datetime(2026, 3, 2, 10, 30, 0)
        assert generate_id("Buy groceries", dt) == generate_id("Buy groceries", dt)

    def test_different_messages_differ(self):
        dt = datetime(2026, 3, 2, 10, 30, 0)
        assert generate_id("Task A", dt) != generate_id("Task B", dt)

    def test_different_timestamps_differ(self):
        dt1 = datetime(2026, 3, 2, 10, 30, 0)
        dt2 = datetime(2026, 3, 2, 10, 30, 1)
        assert generate_id("Buy groceries", dt1) != generate_id("Buy groceries", dt2)

    def test_lowercase_hex(self):
        dt = datetime(2026, 3, 2, 10, 30, 0)
        result = generate_id("test", dt)
        assert result == result.lower()
        int(result, 16)  # must be valid hex


# ---------------------------------------------------------------------------
# Task.__post_init__
# ---------------------------------------------------------------------------

class TestTaskAutoFill:
    def test_auto_fills_created_at(self):
        t = Task(message="Test")
        assert t.created_at != ""
        datetime.fromisoformat(t.created_at)  # must be parseable

    def test_auto_fills_id(self):
        t = Task(message="Test")
        assert len(t.id) == 7

    def test_explicit_created_at_kept(self):
        ts = "2026-01-01T12:00:00"
        t = Task(message="Test", created_at=ts)
        assert t.created_at == ts

    def test_explicit_id_kept(self):
        t = Task(message="Test", id="abc1234")
        assert t.id == "abc1234"

    def test_default_status_is_open(self):
        t = Task(message="Test")
        assert t.status == TaskStatus.OPEN

    def test_status_coercion_from_string(self):
        t = Task(message="Test", status="done")  # type: ignore[arg-type]
        assert t.status == TaskStatus.DONE

    def test_status_coercion_case_insensitive(self):
        t = Task(message="Test", status="WONTDO")  # type: ignore[arg-type]
        assert t.status == TaskStatus.WONTDO

    def test_status_invalid_falls_back_to_open(self):
        t = Task(message="Test", status="garbage")  # type: ignore[arg-type]
        assert t.status == TaskStatus.OPEN


# ---------------------------------------------------------------------------
# Task.completed property
# ---------------------------------------------------------------------------

class TestCompletedProperty:
    def test_false_when_open(self):
        t = Task(message="Test")
        assert t.completed is False

    def test_true_when_done(self):
        t = Task(message="Test", status=TaskStatus.DONE)
        assert t.completed is True

    def test_setter_true_sets_done(self):
        t = Task(message="Test")
        t.completed = True
        assert t.status == TaskStatus.DONE

    def test_setter_false_sets_open(self):
        t = Task(message="Test", status=TaskStatus.DONE)
        t.completed = False
        assert t.status == TaskStatus.OPEN


# ---------------------------------------------------------------------------
# Task.to_dict / Task.from_dict round-trip
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_to_dict_status_is_string(self):
        t = Task(message="Test")
        d = t.to_dict()
        assert isinstance(d["status"], str)
        assert d["status"] == "open"

    def test_round_trip(self):
        t = Task(message="Buy milk", status=TaskStatus.WONTDO)
        restored = Task.from_dict(t.to_dict())
        assert restored.message == t.message
        assert restored.id == t.id
        assert restored.created_at == t.created_at
        assert restored.status == t.status

    def test_from_dict_legacy_completed_true(self):
        data = {"message": "Old task", "completed": True}
        t = Task.from_dict(data)
        assert t.status == TaskStatus.DONE

    def test_from_dict_legacy_completed_false(self):
        data = {"message": "Old task", "completed": False}
        t = Task.from_dict(data)
        assert t.status == TaskStatus.OPEN

    def test_from_dict_invalid_status_defaults_open(self):
        data = {"message": "Bad status", "status": "unknown_value"}
        t = Task.from_dict(data)
        assert t.status == TaskStatus.OPEN
