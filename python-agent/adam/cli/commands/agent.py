"""Agent commands."""

import os
import typer
import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.table import Table

from adam.agent import AgentLoop, LoopConfig
from adam.runtime import RuntimeClient
from adam.orchestration import ExecutionMode
from adam.config import load_config
from adam.storage.vault import get_vault
from adam.providers.registry import load_keys_from_vault, ProviderRegistry
from adam.security import keystore

app = typer.Typer()
console = Console()

# Provider priority order (first available wins)
PROVIDER_PRIORITY = [
    "z-ai-coding",  # z.ai Coding (GLM)
    "z-ai",         # z.ai (GLM)
    "anthropic",    # Anthropic (Claude)
    "openai",       # OpenAI
    "openrouter",   # OpenRouter
    "deepseek",     # DeepSeek
    "ollama",       # Ollama (local)
]


def get_default_provider() -> str:
    """Get the default provider based on what's configured."""
    # First, ensure keys are loaded
    ensure_keys_loaded()
    
    # Check which providers have keys configured
    configured = keystore.list_providers()
    
    if not configured:
        return "anthropic"  # Fallback default
    
    # Return first configured provider by priority
    for provider in PROVIDER_PRIORITY:
        if provider in configured:
            return provider
    
    # If none match priority, return first configured
    return configured[0]


def ensure_keys_loaded():
    """Ensure API keys are loaded from vault into keystore."""
    if keystore.list_providers():
        return
    
    vault = get_vault()
    passphrase = os.environ.get("ADAM_VAULT_PASSPHRASE")
    
    if passphrase and vault.vault_exists and not vault.is_unlocked:
        vault.unlock(passphrase)
    
    if vault.is_unlocked:
        load_keys_from_vault(vault)


def check_runtime() -> RuntimeClient:
    """Check if runtime is available and return client."""
    client = RuntimeClient()
    
    if not os.path.exists(client.socket_path):
        console.print("[red]Error: Adam Runtime is not running[/red]")
        console.print("Start it with: [cyan]adam-runtime[/cyan]")
        raise typer.Exit(1)
    
    if not client.is_available(retries=3, delay=0.5):
        console.print("[red]Error: Adam Runtime is not responding[/red]")
        console.print("Try: [cyan]adam-runtime &[/cyan]")
        raise typer.Exit(1)
    
    return client


def print_hud(provider: str, model: str, stats: dict = None):
    """Print HUD with session info."""
    configured = keystore.list_providers()
    providers_str = ", ".join(configured) if configured else "none"
    key_preview = keystore.preview(provider, 4) if keystore.has(provider) else "not set"
    
    hud_table = Table(show_header=False, box=None, padding=(0, 1))
    hud_table.add_column("Label", style="dim")
    hud_table.add_column("Value", style="cyan")
    
    hud_table.add_row("Provider:", provider)
    hud_table.add_row("API Key:", key_preview)
    hud_table.add_row("Model:", model or "auto")
    hud_table.add_row("Available:", providers_str)
    
    if stats:
        hud_table.add_row("Turns:", str(stats.get("turns", 0)))
        hud_table.add_row("Tool Calls:", str(stats.get("tool_calls", 0)))
    
    console.print(Panel(hud_table, title="[bold]Session Info[/bold]", border_style="dim", expand=False))


def print_error(title: str, message: str, suggestion: str = None):
    """Print formatted error message."""
    console.print(f"\n[bold red]✗ {title}[/bold red]")
    console.print(f"  {message[:300]}")
    if suggestion:
        console.print(f"\n[yellow]→[/yellow] {suggestion}")
    console.print()


def parse_api_error(error_str: str) -> tuple:
    """Parse API error and return (title, suggestion)."""
    error_lower = error_str.lower()
    
    if "credit" in error_lower or "balance" in error_lower or "insufficient" in error_lower:
        return ("API Credits Exhausted", "Add credits or use a different provider.")
    
    if "authentication" in error_lower or "api_key" in error_lower or "invalid" in error_lower:
        return ("API Authentication Failed", "Check your API key.")
    
    if "rate limit" in error_lower:
        return ("Rate Limit Exceeded", "Wait a moment and try again.")
    
    if "timeout" in error_lower:
        return ("Request Timeout", "Try a simpler query.")
    
    return ("API Error", "Check the error message above.")


@app.command()
def start(
    model: str = typer.Option("auto", "--model", "-m", help="Model to use"),
    mode: str = typer.Option("auto", "--mode", help="Execution mode"),
    provider: str = typer.Option(None, "--provider", "-p", help="LLM provider (auto-detects if not set)"),
):
    """Start interactive agent session."""
    client = check_runtime()
    ensure_keys_loaded()
    
    # Auto-detect provider if not specified
    if not provider:
        provider = get_default_provider()
    
    # Check if provider has API key
    if not keystore.has(provider):
        configured = keystore.list_providers()
        if configured:
            print_error(
                "Provider Not Configured",
                f"No API key for '{provider}'",
                f"Configured providers: {', '.join(configured)}. Use: adam agent start -p {configured[0]}"
            )
        else:
            print_error(
                "No API Keys Configured",
                "Run 'adam vault setup-api' to add an API key",
                "Example: adam vault setup-api -p z-ai-coding -k YOUR_KEY"
            )
        raise typer.Exit(1)
    
    print_hud(provider, model)
    
    mode_map = {
        "auto": ExecutionMode.AUTO_PILOT,
        "workflow": ExecutionMode.WORKFLOW,
        "manual": ExecutionMode.USER_PICKED,
    }
    
    loop_config = LoopConfig(
        model=model,
        mode=mode_map.get(mode, ExecutionMode.AUTO_PILOT),
        provider=provider,
    )
    
    agent = AgentLoop(config=loop_config, runtime_client=client)
    
    console.print(Panel.fit(
        "[bold green]Adam Agent[/bold green]\n\n"
        "Type your message and press Enter.\n"
        "Commands: [cyan]/clear[/cyan] [cyan]/exit[/cyan] [cyan]/stats[/cyan] [cyan]/hud[/cyan]",
    ))
    console.print()
    
    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
            
            if user_input.lower() in ("exit", "quit", "/exit", "/quit"):
                console.print("[yellow]Goodbye![/yellow]")
                break
            
            if user_input.lower() == "/clear":
                agent.clear_session()
                console.print("[green]Session cleared[/green]")
                continue
            
            if user_input.lower() == "/stats":
                console.print(f"[dim]{agent.get_stats()}[/dim]")
                continue
            
            if user_input.lower() == "/hud":
                print_hud(provider, agent.state.last_model or model, agent.get_stats())
                continue
            
            console.print("[bold green]Adam:[/bold green]")
            
            try:
                response = asyncio.run(agent.run(user_input))
                if response:
                    console.print(response)
            except Exception as e:
                title, suggestion = parse_api_error(str(e))
                print_error(title, str(e), suggestion)
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
    
    client.close()


@app.command()
def ask(
    message: str = typer.Argument(..., help="Message to send"),
    model: str = typer.Option("auto", "-m"),
    provider: str = typer.Option(None, "-p", help="Provider (auto-detects)"),
):
    """Send a single message to Adam."""
    client = check_runtime()
    ensure_keys_loaded()
    
    if not provider:
        provider = get_default_provider()
    
    if not keystore.has(provider):
        print_error("No API Key", f"Run: adam vault setup-api -p {provider}")
        raise typer.Exit(1)
    
    agent_config = LoopConfig(model=model, mode=ExecutionMode.AUTO_PILOT, provider=provider)
    agent = AgentLoop(config=agent_config, runtime_client=client)
    
    try:
        response = asyncio.run(agent.run(message))
        console.print(response)
    except Exception as e:
        title, suggestion = parse_api_error(str(e))
        print_error(title, str(e), suggestion)
    
    client.close()
