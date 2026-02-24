"""
Adam CLI - Main entry point.
"""

import os
import typer
from rich.console import Console
from typing import Optional

try:
    from adam import __version__
except ImportError:
    __version__ = "0.1.0"

app = typer.Typer(
    name="adam",
    help="Adam - Your Personal AI Assistant",
    add_completion=True,
    no_args_is_help=False,
)
console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
    no_dashboard: bool = typer.Option(False, "--no-dashboard", "-n", help="Skip dashboard"),
):
    """Adam - Personal AI Assistant"""
    if version:
        console.print(f"Adam v{__version__}")
        raise typer.Exit()
    
    if ctx.invoked_subcommand is not None:
        return
    
    if no_dashboard or os.environ.get("ADAM_NO_DASHBOARD"):
        console.print(ctx.get_help())
        return
    
    from adam.cli.dashboard import run_dashboard
    run_dashboard()


from . import agent, vault, profile, sync, cron

app.add_typer(agent.app, name="agent")
app.add_typer(vault.app, name="vault")
app.add_typer(profile.app, name="profile")
app.add_typer(sync.app, name="sync")
app.add_typer(cron.app, name="cron")


@app.command()
def ask(
    message: str = typer.Argument(..., help="Message to send"),
    model: str = typer.Option("auto", "-m", help="Model (or 'auto')"),
    provider: str = typer.Option(None, "-p", help="Provider (auto-detected)"),
):
    """Send a message to Adam."""
    from .agent import ask as agent_ask
    agent_ask(message, model, provider)


@app.command()
def start():
    """Start Adam dashboard."""
    from adam.cli.dashboard import run_dashboard
    run_dashboard()


if __name__ == "__main__":
    app()
