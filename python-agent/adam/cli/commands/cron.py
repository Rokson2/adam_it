"""Cron commands for scheduled tasks."""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


@app.command()
def add(
    name: str = typer.Option(..., "--name", "-n", help="Task name"),
    schedule: str = typer.Option(..., "--schedule", "-s", help="Cron expression"),
    message: str = typer.Option(..., "--message", "-m", help="Message to process"),
):
    """Add a scheduled task."""
    from adam.cron import TaskScheduler

    scheduler = TaskScheduler()
    scheduler.load()

    task = scheduler.add(name, schedule, message)
    console.print(f"[green]Added task: {task.id}[/green]")
    console.print(f"  Name: {task.name}")
    console.print(f"  Schedule: {task.cron_expression}")
    console.print(f"  Next run: {task.next_run}")


@app.command()
def list():
    """List all scheduled tasks."""
    from adam.cron import TaskScheduler

    scheduler = TaskScheduler()
    scheduler.load()

    tasks = scheduler.list_all()

    if not tasks:
        console.print("[yellow]No scheduled tasks[/yellow]")
        return

    table = Table(title="Scheduled Tasks")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Schedule")
    table.add_column("Next Run")
    table.add_column("Enabled")

    for task in tasks:
        table.add_row(
            task.id,
            task.name,
            task.cron_expression,
            str(task.next_run) if task.next_run else "N/A",
            "✓" if task.enabled else "✗",
        )

    console.print(table)


@app.command()
def remove(
    task_id: str = typer.Argument(..., help="Task ID to remove"),
):
    """Remove a scheduled task."""
    from adam.cron import TaskScheduler

    scheduler = TaskScheduler()
    scheduler.load()

    if scheduler.remove(task_id):
        console.print(f"[green]Removed task: {task_id}[/green]")
    else:
        console.print(f"[red]Task not found: {task_id}[/red]")
        raise typer.Exit(1)


@app.command()
def enable(
    task_id: str = typer.Argument(..., help="Task ID"),
):
    """Enable a scheduled task."""
    console.print("[dim]Task enable/disable coming soon[/dim]")


@app.command()
def disable(
    task_id: str = typer.Argument(..., help="Task ID"),
):
    """Disable a scheduled task."""
    console.print("[dim]Task enable/disable coming soon[/dim]")
