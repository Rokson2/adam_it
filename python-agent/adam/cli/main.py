"""
Adam CLI - Main entry point.
"""

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
)
console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit"),
):
    """Adam - Personal AI Assistant"""
    if version:
        console.print(f"Adam v{__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


from . import agent, vault, profile, sync, cron

app.add_typer(agent.app, name="agent")
app.add_typer(vault.app, name="vault")
app.add_typer(profile.app, name="profile")
app.add_typer(sync.app, name="sync")
app.add_typer(cron.app, name="cron")


@app.command()
def ask(
    message: str = typer.Argument(..., help="Message to send to Adam"),
    model: str = typer.Option("auto", "--model", "-m", help="Model to use"),
):
    """Send a single message to Adam (shortcut for 'adam agent ask')"""
    from .agent import ask as agent_ask

    agent_ask(message, model)


if __name__ == "__main__":
    app()
