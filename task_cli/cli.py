"""CLI commands — entry point for `tsk`."""

from datetime import datetime
from itertools import groupby

import click

from task_cli.models import Task, TaskStatus
from task_cli.storage import add_task, load_tasks, complete_task, find_task_by_id, delete_task, wont_do_task, edit_task


def min_unique_prefix_lengths(ids: list[str]) -> dict[str, int]:
    """Return the minimum prefix length needed to uniquely identify each ID."""
    result = {}
    for id in ids:
        for k in range(1, len(id) + 1):
            if sum(1 for other in ids if other.startswith(id[:k])) == 1:
                result[id] = k
                break
        else:
            result[id] = len(id)
    return result


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
def main():
    """tsk — A simple CLI task manager."""


@main.command()
@click.argument("message")
def add(message: str):
    """Create a new task."""
    task = Task(message=message)
    add_task(task)
    click.echo(f"Added task [{task.id}] {task.message}")


@main.command("list")
@click.option("--all", "-a", "show_all", is_flag=True, help="Show all tasks including done and won't-do.")
def list_tasks(show_all: bool):
    """Show tasks. By default only incomplete tasks are shown."""
    all_tasks = load_tasks()
    tasks = all_tasks if show_all else [t for t in all_tasks if t.status == TaskStatus.OPEN]

    if not tasks:
        click.echo("No tasks.")
        return

    # Sort by created_at
    tasks.sort(key=lambda t: t.created_at)

    # Compute minimum unique prefix lengths against ALL tasks, including non-displayed ones
    prefix_lengths = min_unique_prefix_lengths([t.id for t in all_tasks])

    # Group by date
    def date_key(t: Task) -> str:
        return datetime.fromisoformat(t.created_at).strftime("%Y-%m-%d")

    for date, group in groupby(tasks, key=date_key):
        click.echo(date)
        for t in group:
            status = "[x]" if t.status == TaskStatus.DONE else "[-]" if t.status == TaskStatus.WONTDO else "[ ]"
            k = prefix_lengths.get(t.id, len(t.id))
            formatted_id = t.id[:k] + click.style(t.id[k:], dim=True)
            click.echo(f"  {status} {formatted_id}  {t.message}")
        click.echo()


@main.command()
@click.argument("task_id")
def done(task_id: str):
    """Mark a task as complete by full or partial ID."""
    task = complete_task(task_id)
    if task:
        click.echo(f"Completed: {task.message}")
    else:
        click.echo(f"No unique task found matching '{task_id}'.")


@main.command("wontdo")
@click.argument("task_id")
def wontdo(task_id: str):
    """Mark a task as won't-do by full or partial ID."""
    task = wont_do_task(task_id)
    if task:
        click.echo(f"Marked won't-do: {task.message}")
    else:
        click.echo(f"No unique task found matching '{task_id}'.")


@main.command()
@click.argument("task_id")
@click.argument("message")
def edit(task_id: str, message: str):
    """Edit the text of an existing task by full or partial ID."""
    task = edit_task(task_id, message)
    if task:
        click.echo(f"Updated: {task.message}")
    else:
        click.echo(f"No unique task found matching '{task_id}'.")


@main.command()
@click.argument("task_id")
@click.option("--yes", "-y", is_flag=True, help="Don't prompt for confirmation.")
def delete(task_id: str, yes: bool):
    """Delete a task by full or partial ID."""
    task = find_task_by_id(task_id)
    if not task:
        click.echo(f"No unique task found matching '{task_id}'.")
        return
    if yes or click.confirm(f"Delete task [{task.id}] {task.message}?"):
        deleted = delete_task(task.id)
        if deleted:
            click.echo(f"Deleted: {deleted.message}")
        else:
            click.echo("Failed to delete task.")
    else:
        click.echo("Aborted.")
