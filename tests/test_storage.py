"""Unit tests for task_cli/storage.py."""

import pytest

from task_cli.models import Task, TaskStatus
from task_cli import storage as st


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_task(message: str, status: TaskStatus = TaskStatus.OPEN) -> Task:
    return Task(message=message, status=status)


# ---------------------------------------------------------------------------
# ensure_storage / load_tasks on empty store
# ---------------------------------------------------------------------------

class TestEnsureAndLoad:
    def test_creates_file_on_first_load(self, isolated_storage):
        tasks = st.load_tasks()
        assert (isolated_storage / "tasks.md").exists()
        assert tasks == []

    def test_loads_empty_list_from_header_only_file(self, isolated_storage):
        (isolated_storage / "tasks.md").write_text("# Tasks\n\n")
        assert st.load_tasks() == []


# ---------------------------------------------------------------------------
# save_tasks / load_tasks round-trip
# ---------------------------------------------------------------------------

class TestSaveLoad:
    def test_round_trip_single_open_task(self, isolated_storage):
        task = make_task("Buy milk")
        st.save_tasks([task])
        loaded = st.load_tasks()
        assert len(loaded) == 1
        assert loaded[0].message == "Buy milk"
        assert loaded[0].id == task.id
        assert loaded[0].status == TaskStatus.OPEN

    def test_round_trip_all_statuses(self, isolated_storage):
        tasks = [
            make_task("Open task", TaskStatus.OPEN),
            make_task("Done task", TaskStatus.DONE),
            make_task("Wontdo task", TaskStatus.WONTDO),
        ]
        st.save_tasks(tasks)
        loaded = {t.message: t for t in st.load_tasks()}
        assert loaded["Open task"].status == TaskStatus.OPEN
        assert loaded["Done task"].status == TaskStatus.DONE
        assert loaded["Wontdo task"].status == TaskStatus.WONTDO

    def test_groups_by_date_heading(self, isolated_storage):
        task = make_task("Check heading")
        st.save_tasks([task])
        content = (isolated_storage / "tasks.md").read_text()
        assert "## " in content  # a day heading was written

    def test_multiple_tasks_preserved(self, isolated_storage):
        tasks = [make_task(f"Task {i}") for i in range(5)]
        st.save_tasks(tasks)
        loaded = st.load_tasks()
        assert len(loaded) == 5


# ---------------------------------------------------------------------------
# add_task
# ---------------------------------------------------------------------------

class TestAddTask:
    def test_adds_task(self, isolated_storage):
        st.add_task(make_task("New task"))
        assert len(st.load_tasks()) == 1

    def test_multiple_adds_accumulate(self, isolated_storage):
        st.add_task(make_task("Task A"))
        st.add_task(make_task("Task B"))
        assert len(st.load_tasks()) == 2

    def test_id_collision_resolved(self, isolated_storage, monkeypatch):
        """When two tasks produce the same ID, the second gets a new unique ID."""
        fixed_id = "aabbccd"
        call_count = {"n": 0}

        original_generate = st.generate_id if hasattr(st, "generate_id") else None

        import task_cli.models as models_module
        original = models_module.generate_id

        def patched(message, created_at):
            call_count["n"] += 1
            # Force same ID for first two calls to simulate collision
            if call_count["n"] <= 2:
                return fixed_id
            return original(message, created_at)

        monkeypatch.setattr(models_module, "generate_id", patched)

        # Pre-seed a task with the fixed ID
        task1 = Task(message="First", id=fixed_id, created_at="2026-01-01T10:00:00")
        st.save_tasks([task1])

        # Now add a second task — storage.add_task should resolve the collision
        task2 = Task(message="Second")
        task2.id = fixed_id  # manually force same ID
        st.add_task(task2)

        loaded = st.load_tasks()
        ids = [t.id for t in loaded]
        assert len(set(ids)) == 2, "IDs should be unique after collision resolution"


# ---------------------------------------------------------------------------
# find_task_by_id
# ---------------------------------------------------------------------------

class TestFindTaskById:
    def test_finds_by_full_id(self, isolated_storage):
        task = make_task("Find me")
        st.save_tasks([task])
        found = st.find_task_by_id(task.id)
        assert found is not None
        assert found.message == "Find me"

    def test_finds_by_partial_id(self, isolated_storage):
        task = make_task("Find me partial")
        st.save_tasks([task])
        found = st.find_task_by_id(task.id[:3])
        assert found is not None
        assert found.id == task.id

    def test_returns_none_on_no_match(self, isolated_storage):
        st.save_tasks([make_task("Some task")])
        assert st.find_task_by_id("zzzzzzz") is None

    def test_returns_none_on_ambiguous(self, isolated_storage):
        # Two tasks whose IDs share the same prefix '0' (unlikely but force it)
        t1 = Task(message="A", id="0000001", created_at="2026-01-01T10:00:00")
        t2 = Task(message="B", id="0000002", created_at="2026-01-01T10:00:01")
        st.save_tasks([t1, t2])
        assert st.find_task_by_id("000000") is None


# ---------------------------------------------------------------------------
# complete_task
# ---------------------------------------------------------------------------

class TestCompleteTask:
    def test_marks_done(self, isolated_storage):
        task = make_task("Finish report")
        st.save_tasks([task])
        result = st.complete_task(task.id)
        assert result is not None
        assert result.status == TaskStatus.DONE
        assert st.load_tasks()[0].status == TaskStatus.DONE

    def test_returns_none_on_no_match(self, isolated_storage):
        st.save_tasks([make_task("Task")])
        assert st.complete_task("zzzzzzz") is None

    def test_partial_id_works(self, isolated_storage):
        task = make_task("Partial done")
        st.save_tasks([task])
        result = st.complete_task(task.id[:4])
        assert result is not None
        assert result.status == TaskStatus.DONE


# ---------------------------------------------------------------------------
# wont_do_task
# ---------------------------------------------------------------------------

class TestWontDoTask:
    def test_marks_wontdo(self, isolated_storage):
        task = make_task("Skip this")
        st.save_tasks([task])
        result = st.wont_do_task(task.id)
        assert result is not None
        assert result.status == TaskStatus.WONTDO
        assert st.load_tasks()[0].status == TaskStatus.WONTDO

    def test_returns_none_on_no_match(self, isolated_storage):
        st.save_tasks([make_task("Task")])
        assert st.wont_do_task("zzzzzzz") is None


# ---------------------------------------------------------------------------
# delete_task
# ---------------------------------------------------------------------------

class TestDeleteTask:
    def test_deletes_task(self, isolated_storage):
        task = make_task("Delete me")
        st.save_tasks([task])
        deleted = st.delete_task(task.id)
        assert deleted is not None
        assert deleted.message == "Delete me"
        assert st.load_tasks() == []

    def test_returns_none_on_no_match(self, isolated_storage):
        st.save_tasks([make_task("Task")])
        assert st.delete_task("zzzzzzz") is None

    def test_only_deletes_matched_task(self, isolated_storage):
        t1 = make_task("Keep me")
        t2 = make_task("Delete me")
        st.save_tasks([t1, t2])
        st.delete_task(t2.id)
        remaining = st.load_tasks()
        assert len(remaining) == 1
        assert remaining[0].message == "Keep me"


# ---------------------------------------------------------------------------
# edit_task
# ---------------------------------------------------------------------------


class TestEditTask:
    def test_edits_message(self, isolated_storage):
        task = make_task("Original")
        st.save_tasks([task])
        updated = st.edit_task(task.id, "Changed")
        assert updated is not None
        assert updated.message == "Changed"
        loaded = st.load_tasks()[0]
        assert loaded.message == "Changed"
        assert loaded.id == task.id
        assert loaded.created_at == task.created_at
        assert loaded.status == task.status

    def test_partial_id_works(self, isolated_storage):
        task = make_task("Partial edit")
        st.save_tasks([task])
        updated = st.edit_task(task.id[:4], "New")
        assert updated is not None
        assert updated.message == "New"
        loaded = st.load_tasks()[0]
        assert loaded.id == task.id
        assert loaded.created_at == task.created_at
        assert loaded.status == task.status

    def test_returns_none_on_no_match(self, isolated_storage):
        st.save_tasks([make_task("Task")])
        assert st.edit_task("zzzzzzz", "X") is None

    def test_returns_none_on_ambiguous(self, isolated_storage):
        t1 = make_task("A", TaskStatus.OPEN)
        t1.id = "0000001"
        t2 = make_task("B", TaskStatus.OPEN)
        t2.id = "0000002"
        st.save_tasks([t1, t2])
        assert st.edit_task("000000", "X") is None
