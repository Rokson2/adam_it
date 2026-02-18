"""Agent commands."""

import os
import typer
import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.live import Live
from rich.table import Table
from rich.text import Text
from typing import Optional

from adam.agent import AgentLoop, LoopConfig
from adam.runtime import RuntimeClient
from adam.orchestration import ExecutionMode
from adam.config import load_config
from adam.storage.vault import get_vault
from adam.providers.registry import load_keys_from_vault, ProviderRegistry
from adam.security import keystore

app = typer.Typer()
console = Console()


def ensure_keys_loaded():
    """Ensure API keys are loaded from vault into keystore."""
    # Check if we already have keys
    if keystore.list_providers():
        return
    
    # Try to load from vault
    vault = get_vault()
    passphrase = os.environ.get("ADAM_VAULT_PASSPHRASE")
    
    if passphrase and vault.vault_exists and not vault.is_unlocked:
        vault.unlock(passphrase)
    
    if vault.is_unlocked:
        load_keys_from_vault(vault)


def check_runtime() -> RuntimeClient:
    """Check if runtime is available and return client."""
    client = RuntimeClient()
    
    # First check if socket exists
    if not os.path.exists(client.socket_path):
        console.print("[red]Error: Adam Runtime is not running[/red]")
        console.print(f"[dim]Socket not found: {client.socket_path}[/dim]")
        console.print("\nStart it with: [cyan]adam-runtime[/cyan]")
        console.print("\nOr if using Docker, ensure the container was started correctly:")
        console.print("  [dim]docker-compose -f docker-compose.test.yml up -d[/dim]")
        raise typer.Exit(1)
    
    # Try to connect with retries
    if not client.is_available(retries=3, delay=0.5):
        console.print("[red]Error: Adam Runtime is not responding[/red]")
        console.print("[dim]The socket exists but the runtime is not accepting connections.[/dim]")
        console.print("\nTry restarting the runtime:")
        console.print("  [cyan]adam-runtime &[/cyan]")
        raise typer.Exit(1)
    
    return client


def print_hud(provider: str, model: str, stats: dict = None):
    """Print HUD with session info."""
    # Get configured providers
    configured = ProviderRegistry.list_configured()
    providers_str = ", ".join(configured) if configured else "none"
    
    # Key preview
    key_preview = keystore.preview(provider, 4) if keystore.has(provider) else "not set"
    
    hud_table = Table(show_header=False, box=None, padding=(0, 1))
    hud_table.add_column("Label", style="dim")
    hud_table.add_column("Value", style="cyan")
    
    hud_table.add_row("Provider:", provider)
    hud_table.add_row("API Key:", key_preview)
    hud_table.add_row("Model:", model or "auto")
    hud_table.add_row("Configured:", providers_str)
    
    if stats:
        hud_table.add_row("Turns:", str(stats.get("turns", 0)))
        hud_table.add_row("Tool Calls:", str(stats.get("tool_calls", 0)))
        if stats.get("errors"):
            hud_table.add_row("Errors:", str(len(stats["errors"])))
    
    console.print(Panel(hud_table, title="[bold]Session Info[/bold]", border_style="dim", expand=False))


def print_error(title: str, message: str, suggestion: str = None, url: str = None):
    """Print formatted error message with troubleshooting help."""
    console.print(f"\n[bold red]✗ {title}[/bold red]")
    
    # Try to extract useful info from error message
    if "{" in message and "error" in message.lower():
        # It's a JSON error, try to parse it
        try:
            import json
            # Find JSON part
            start = message.find("{")
            end = message.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = message[start:end]
                data = json.loads(json_str)
                if "error" in data and "message" in data["error"]:
                    console.print(f"  [yellow]{data['error']['message']}[/yellow]")
                else:
                    console.print(f"  {message[:200]}")
        except:
            console.print(f"  {message[:200]}")
    else:
        console.print(f"  {message[:200]}")
    
    if suggestion:
        console.print(f"\n[yellow]→ Suggestion:[/yellow] {suggestion}")
    if url:
        console.print(f"[dim]   {url}[/dim]")
    console.print()


def parse_api_error(error_str: str) -> tuple:
    """Parse API error and return (title, suggestion, url)."""
    error_lower = error_str.lower()
    
    if "credit balance is too low" in error_lower or "insufficient" in error_lower:
        return (
            "API Credits Exhausted",
            "Add credits to your Anthropic account, or use a different provider.",
            "https://console.anthropic.com/settings/billing"
        )
    
    if "authentication" in error_lower or "api_key" in error_lower or "invalid api key" in error_lower:
        return (
            "API Authentication Failed",
            "Your API key may be invalid or expired. Check your key.",
            "https://console.anthropic.com/settings/keys"
        )
    
    if "rate limit" in error_lower:
        return (
            "Rate Limit Exceeded",
            "Wait a moment and try again, or switch to a different provider.",
            None
        )
    
    if "timeout" in error_lower:
        return (
            "Request Timeout",
            "The API took too long. Try a simpler query.",
            None
        )
    
    if "model" in error_lower and "not found" in error_lower:
        return (
            "Model Not Available",
            "The requested model doesn't exist. Try using 'auto' for model selection.",
            None
        )
    
    if "overloaded" in error_lower:
        return (
            "API Overloaded",
            "Anthropic's servers are busy. Wait a moment and try again.",
            None
        )
    
    return ("API Error", "Check the error message above.", None)


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
    client = check_runtime()
    
    # Load API keys from vault
    ensure_keys_loaded()
    
    # Check if provider has API key
    if not keystore.has(provider):
        print_error(
            "API Key Not Configured",
            f"No API key found for provider '{provider}'",
            f"Run: [cyan]adam vault setup-api[/cyan] to add your API key"
        )
        raise typer.Exit(1)
    
    # Show HUD
    print_hud(provider, model)
    
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
            "[bold green]Adam Agent[/bold green]\n\n"
            "Type your message and press Enter.\n"
            "Commands: [cyan]/clear[/cyan], [cyan]/exit[/cyan], [cyan]/stats[/cyan], [cyan]/hud[/cyan]",
        )
    )
    console.print()

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
            
            if user_input.lower() in ("/hud",):
                stats = agent.get_stats()
                print_hud(provider, agent.state.last_model or model, stats)
                continue

            console.print("[bold green]Adam:[/bold green]")

            def on_response(text):
                console.print(Markdown(text))

            # Run agent
            try:
                response = asyncio.run(agent.run(user_input, on_response=on_response))
                if response:
                    console.print(Markdown(response))
            except Exception as e:
                error_str = str(e)
                title, suggestion, url = parse_api_error(error_str)
                print_error(title, error_str, suggestion, url)

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            print_error("Unexpected Error", str(e))

    client.close()


@app.command()
def ask(
    message: str = typer.Argument(..., help="Message to send"),
    model: str = typer.Option("auto", "--model", "-m"),
    provider: str = typer.Option("anthropic", "--provider", "-p"),
):
    """Send a single message to Adam."""
    client = check_runtime()
    
    # Load API keys from vault
    ensure_keys_loaded()
    
    # Check if provider has API key
    if not keystore.has(provider):
        print_error(
            "API Key Not Configured",
            f"No API key found for provider '{provider}'",
            "Run: adam vault setup-api"
        )
        raise typer.Exit(1)

    agent_config = LoopConfig(
        model=model,
        mode=ExecutionMode.AUTO_PILOT,
        provider=provider,
    )

    agent = AgentLoop(config=agent_config, runtime_client=client)

    try:
        response = asyncio.run(agent.run(message))
        console.print(Markdown(response))
    except Exception as e:
        error_str = str(e)
        title, suggestion, url = parse_api_error(error_str)
        print_error(title, error_str, suggestion, url)

    client.close()
