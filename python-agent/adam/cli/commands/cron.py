"""Scheduled task commands."""

import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from adam.storage.vault import get_vault

app = typer.Typer()
console = Console()


@app.command("add")
def add_task(
    name: str = typer.Option(..., "-n", "--name", help="Task name"),
    schedule: str = typer.Option(..., "-s", "--schedule", help="Cron schedule"),
    task: str = typer.Option(..., "-t", "--task", help="Task to run"),
):
    """Add a scheduled task."""
    # TODO: Implement task storage
    console.print(f"[green]Added task '{name}'[/green]")
    console.print(f"  Schedule: {schedule}")
    console.print(f"  Task: {task}")


@app.command("list")
def list_tasks():
    """List scheduled tasks."""
    # Built-in system tasks
    tasks = [
        {"name": "model-update", "schedule": "0 0 * * 0", "task": "Check for model updates", "type": "system"},
        {"name": "vault-backup", "schedule": "0 2 * * *", "task": "Backup vault", "type": "system"},
    ]
    
    table = Table(title="Scheduled Tasks")
    table.add_column("Name", style="cyan")
    table.add_column("Schedule")
    table.add_column("Task")
    table.add_column("Type")
    
    for t in tasks:
        table.add_row(t["name"], t["schedule"], t["task"], t["type"])
    
    console.print(table)


@app.command("run")
def run_task(
    name: str = typer.Argument(..., help="Task name to run"),
):
    """Run a task immediately."""
    if name == "model-update":
        console.print("[cyan]Checking for model updates...[/cyan]")
        from adam.providers.models import get_model_registry
        import asyncio
        registry = get_model_registry()
        result = asyncio.run(registry.check_for_updates())
        console.print(f"[green]Model update check complete[/green]")
    else:
        console.print(f"[red]Unknown task: {name}[/red]")
        raise typer.Exit(1)
