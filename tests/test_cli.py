"""Integration tests for task_cli/cli.py via Click's CliRunner."""

import pytest
from click.testing import CliRunner

from task_cli.cli import main
from task_cli.models import Task, TaskStatus
from task_cli import storage as st


@pytest.fixture
def runner():
    return CliRunner()


def test_help_short_and_long(runner):
    result_long = runner.invoke(main, ["--help"])
    assert result_long.exit_code == 0
    assert "Usage:" in result_long.output
    result_short = runner.invoke(main, ["-h"])
    assert result_short.exit_code == 0
    assert "Usage:" in result_short.output


# ---------------------------------------------------------------------------
# tsk add
# ---------------------------------------------------------------------------

class TestAddCommand:
    def test_adds_task_and_prints_id(self, runner, isolated_storage):
        result = runner.invoke(main, ["add", "Buy groceries"])
        assert result.exit_code == 0
        assert "Added task" in result.output
        assert "Buy groceries" in result.output

    def test_task_persisted_after_add(self, runner, isolated_storage):
        runner.invoke(main, ["add", "Persisted task"])
        tasks = st.load_tasks()
        assert len(tasks) == 1
        assert tasks[0].message == "Persisted task"

    def test_multiple_adds(self, runner, isolated_storage):
        runner.invoke(main, ["add", "Task 1"])
        runner.invoke(main, ["add", "Task 2"])
        assert len(st.load_tasks()) == 2


# ---------------------------------------------------------------------------
# tsk list
# ---------------------------------------------------------------------------

class TestListCommand:
    def test_no_tasks_prints_message(self, runner, isolated_storage):
        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0
        assert "No tasks." in result.output

    def test_shows_open_tasks(self, runner, isolated_storage):
        runner.invoke(main, ["add", "Open task"])
        result = runner.invoke(main, ["list"])
        assert "Open task" in result.output
        assert "[ ]" in result.output

    def test_hides_done_without_all_flag(self, runner, isolated_storage):
        task = Task(message="Done task", status=TaskStatus.DONE)
        st.save_tasks([task])
        result = runner.invoke(main, ["list"])
        assert "Done task" not in result.output

    @pytest.mark.parametrize("flag", ["--all", "-a"])
    def test_shows_done_with_all_flag(self, runner, isolated_storage, flag):
        task = Task(message="Done task", status=TaskStatus.DONE)
        st.save_tasks([task])
        result = runner.invoke(main, ["list", flag])
        assert "Done task" in result.output
        assert "[x]" in result.output

    def test_shows_wontdo_with_all_flag(self, runner, isolated_storage):
        task = Task(message="Skip this", status=TaskStatus.WONTDO)
        st.save_tasks([task])
        result = runner.invoke(main, ["list", "--all"])
        assert "Skip this" in result.output
        assert "[-]" in result.output

    def test_output_grouped_by_date(self, runner, isolated_storage):
        runner.invoke(main, ["add", "Check grouping"])
        result = runner.invoke(main, ["list"])
        # A date header like "2026-03-04" should appear
        import re
        assert re.search(r"\d{4}-\d{2}-\d{2}", result.output)


# ---------------------------------------------------------------------------
# tsk done
# ---------------------------------------------------------------------------

class TestDoneCommand:
    def test_marks_task_done(self, runner, isolated_storage):
        runner.invoke(main, ["add", "Finish report"])
        task = st.load_tasks()[0]
        result = runner.invoke(main, ["done", task.id])
        assert result.exit_code == 0
        assert "Completed" in result.output
        assert st.load_tasks()[0].status == TaskStatus.DONE

    def test_partial_id_works(self, runner, isolated_storage):
        runner.invoke(main, ["add", "Partial done"])
        task = st.load_tasks()[0]
        result = runner.invoke(main, ["done", task.id[:3]])
        assert result.exit_code == 0
        assert "Completed" in result.output

    def test_no_match_prints_error(self, runner, isolated_storage):
        result = runner.invoke(main, ["done", "zzzzzzz"])
        assert result.exit_code == 0
        assert "No unique task found" in result.output

    def test_ambiguous_id_prints_error(self, runner, isolated_storage):
        t1 = Task(message="A", id="0000001", created_at="2026-01-01T10:00:00")
        t2 = Task(message="B", id="0000002", created_at="2026-01-01T10:00:01")
        st.save_tasks([t1, t2])
        result = runner.invoke(main, ["done", "000000"])
        assert "No unique task found" in result.output


# ---------------------------------------------------------------------------
# tsk wontdo
# ---------------------------------------------------------------------------

class TestWontdoCommand:
    def test_marks_task_wontdo(self, runner, isolated_storage):
        runner.invoke(main, ["add", "Skip this"])
        task = st.load_tasks()[0]
        result = runner.invoke(main, ["wontdo", task.id])
        assert result.exit_code == 0
        assert "won't-do" in result.output
        assert st.load_tasks()[0].status == TaskStatus.WONTDO

    def test_no_match_prints_error(self, runner, isolated_storage):
        result = runner.invoke(main, ["wontdo", "zzzzzzz"])
        assert "No unique task found" in result.output


# ---------------------------------------------------------------------------
# tsk delete
# ---------------------------------------------------------------------------

class TestDeleteCommand:
    def test_deletes_with_yes_flag(self, runner, isolated_storage):
        runner.invoke(main, ["add", "Delete me"])
        task = st.load_tasks()[0]
        result = runner.invoke(main, ["delete", task.id, "--yes"])
        assert result.exit_code == 0
        assert "Deleted" in result.output
        assert st.load_tasks() == []

    def test_delete_prompts_for_confirmation(self, runner, isolated_storage):
        runner.invoke(main, ["add", "Confirm delete"])
        task = st.load_tasks()[0]
        # Answer 'y' to the confirmation prompt
        result = runner.invoke(main, ["delete", task.id], input="y\n")
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_delete_aborted_on_no(self, runner, isolated_storage):
        runner.invoke(main, ["add", "Keep me"])
        task = st.load_tasks()[0]
        result = runner.invoke(main, ["delete", task.id], input="n\n")
        assert "Aborted" in result.output
        assert len(st.load_tasks()) == 1

    def test_no_match_prints_error(self, runner, isolated_storage):
        result = runner.invoke(main, ["delete", "zzzzzzz", "--yes"])
        assert "No unique task found" in result.output

    def test_partial_id_with_yes(self, runner, isolated_storage):
        runner.invoke(main, ["add", "Partial delete"])
        task = st.load_tasks()[0]
        result = runner.invoke(main, ["delete", task.id[:4], "--yes"])
        assert result.exit_code == 0
        assert "Deleted" in result.output


# ---------------------------------------------------------------------------
# tsk edit
# ---------------------------------------------------------------------------


class TestEditCommand:
    def test_edits_task_message(self, runner, isolated_storage):
        runner.invoke(main, ["add", "Buy potatoes"])
        task = st.load_tasks()[0]
        result = runner.invoke(main, ["edit", task.id, "Buy tomatoes"])
        assert result.exit_code == 0
        assert "Updated" in result.output
        loaded = st.load_tasks()[0]
        assert loaded.message == "Buy tomatoes"
        assert loaded.id == task.id
        assert loaded.created_at == task.created_at
        assert loaded.status == task.status

    def test_partial_id_works(self, runner, isolated_storage):
        runner.invoke(main, ["add", "Partial edit"]) 
        task = st.load_tasks()[0]
        result = runner.invoke(main, ["edit", task.id[:4], "Edited message"]) 
        assert result.exit_code == 0
        assert "Updated" in result.output
        loaded = st.load_tasks()[0]
        assert loaded.message == "Edited message"
        assert loaded.id == task.id
        assert loaded.created_at == task.created_at
        assert loaded.status == task.status

    def test_no_match_prints_error(self, runner, isolated_storage):
        result = runner.invoke(main, ["edit", "zzzzzzz", "Whatever"]) 
        assert "No unique task found" in result.output

    def test_ambiguous_id_prints_error(self, runner, isolated_storage):
        t1 = Task(message="A", id="0000001", created_at="2026-01-01T10:00:00")
        t2 = Task(message="B", id="0000002", created_at="2026-01-01T10:00:01")
        st.save_tasks([t1, t2])
        result = runner.invoke(main, ["edit", "000000", "New"]) 
        assert "No unique task found" in result.output
