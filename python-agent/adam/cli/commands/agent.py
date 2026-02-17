"""Agent commands."""

import typer
import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from typing import Optional

from adam.agent import AgentLoop, LoopConfig
from adam.runtime import RuntimeClient
from adam.orchestration import ExecutionMode
from adam.config import load_config

app = typer.Typer()
console = Console()


@app.callback()
def agent_main():
    """Agent commands for interacting with Adam."""
    pass


@app.command()
def start(
    model: str = typer.Option(
        "auto", "--model", "-m", help="Model to use (or 'auto' for complexity-based)"
    ),
    mode: str = typer.Option("auto", "--mode", help="Execution mode: auto, workflow, manual"),
    provider: str = typer.Option("anthropic", "--provider", "-p", help="LLM provider"),
):
    """Start interactive agent session."""
    # Check runtime
    client = RuntimeClient()
    if not client.is_available():
        console.print("[red]Error: Adam Runtime is not running[/red]")
        console.print("Start it with: [cyan]adam-runtime[/cyan]")
        raise typer.Exit(1)

    # Map mode string to enum
    mode_map = {
        "auto": ExecutionMode.AUTO_PILOT,
        "workflow": ExecutionMode.WORKFLOW,
        "manual": ExecutionMode.USER_PICKED,
    }

    # Load config
    config = load_config()

    # Create agent config
    loop_config = LoopConfig(
        model=model,
        mode=mode_map.get(mode, ExecutionMode.AUTO_PILOT),
        provider=provider,
    )

    # Create agent
    agent = AgentLoop(
        config=loop_config,
        runtime_client=client,
    )

    console.print(
        Panel.fit(
            "[bold green]Adam Agent[/bold green]\n"
            f"Model: {model}\n"
            f"Mode: {mode}\n"
            f"Provider: {provider}\n\n"
            "Type your message and press Enter.\n"
            "Commands: /clear, /exit, /stats",
        )
    )

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")

            # Handle commands
            if user_input.lower() in ("exit", "quit", "/exit", "/quit"):
                console.print("[yellow]Goodbye![/yellow]")
                break

            if user_input.lower() in ("/clear",):
                agent.clear_session()
                console.print("[green]Session cleared[/green]")
                continue

            if user_input.lower() in ("/stats",):
                stats = agent.get_stats()
                console.print(f"[dim]Stats: {stats}[/dim]")
                continue

            console.print("[bold green]Adam:[/bold green]")

            def on_response(text):
                console.print(Markdown(text))

            # Run agent
            response = asyncio.run(agent.run(user_input, on_response=on_response))

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    client.close()


@app.command()
def ask(
    message: str = typer.Argument(..., help="Message to send"),
    model: str = typer.Option("auto", "--model", "-m"),
    provider: str = typer.Option("anthropic", "--provider", "-p"),
):
    """Send a single message to Adam."""
    client = RuntimeClient()
    if not client.is_available():
        console.print("[red]Runtime not available[/red]")
        raise typer.Exit(1)

    agent_config = LoopConfig(
        model=model,
        mode=ExecutionMode.AUTO_PILOT,
        provider=provider,
    )

    agent = AgentLoop(config=agent_config, runtime_client=client)

    response = asyncio.run(agent.run(message))
    console.print(Markdown(response))

    client.close()
