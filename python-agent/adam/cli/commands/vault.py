"""Vault commands for secret management."""

import os
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.layout import Layout
from rich.align import Align
from rich import box

from adam.storage.vault import Vault, VaultLockedError, get_vault
from adam.providers.registry import load_keys_from_vault
from adam.security import keystore

app = typer.Typer()
console = Console()

# Environment variable for session passphrase
VAULT_SESSION_ENV = "ADAM_VAULT_PASSPHRASE"

# Supported API providers
API_PROVIDERS = {
    "anthropic": {
        "key": "ANTHROPIC_API_KEY",
        "name": "Anthropic (Claude)",
        "description": "Claude 3.5 Sonnet, Haiku, Opus",
        "url": "https://console.anthropic.com/",
    },
    "openai": {
        "key": "OPENAI_API_KEY",
        "name": "OpenAI (GPT-4)",
        "description": "GPT-4, GPT-4 Turbo, GPT-3.5",
        "url": "https://platform.openai.com/api-keys",
    },
    "openrouter": {
        "key": "OPENROUTER_API_KEY",
        "name": "OpenRouter",
        "description": "Access to 100+ models (Claude, GPT, Llama, etc.)",
        "url": "https://openrouter.ai/keys",
    },
    "z-ai": {
        "key": "ZAI_API_KEY",
        "name": "z.ai",
        "description": "z.ai models",
        "url": "https://z.ai/",
    },
    "z-ai-coding": {
        "key": "ZAI_CODING_API_KEY",
        "name": "z.ai Coding",
        "description": "z.ai coding-optimized models",
        "url": "https://z.ai/",
    },
    "deepseek": {
        "key": "DEEPSEEK_API_KEY",
        "name": "DeepSeek",
        "description": "DeepSeek Chat, Coder",
        "url": "https://platform.deepseek.com/",
    },
    "ollama": {
        "key": "OLLAMA_BASE_URL",
        "name": "Ollama (Local)",
        "description": "Run models locally (no API key needed)",
        "url": "http://localhost:11434",
    },
}


def print_welcome():
    """Print welcome message with basic commands."""
    welcome_text = """
[bold cyan]Welcome to Adam - Your Personal AI Assistant![/bold cyan]

[dim]── Basic Commands ──[/dim]

  [yellow]adam vault unlock[/yellow]        Unlock your vault (required first time)
  [yellow]adam vault setup-api[/yellow]     Add API keys for LLM providers
  [yellow]adam agent ask "..."[/yellow]     Ask Adam a question
  [yellow]adam agent start[/yellow]         Start interactive session

[dim]── Vault Commands ──[/dim]

  [yellow]adam vault add KEY[/yellow]       Add a secret
  [yellow]adam vault get KEY[/yellow]       Retrieve a secret
  [yellow]adam vault list[/yellow]          List all keys
  [yellow]adam vault lock[/yellow]          Lock the vault

[dim]── Security ──[/dim]

  [green]✓[/green] API keys are encrypted at rest
  [green]✓[/green] Keys are never exposed to LLM prompts
  [green]✓[/green] Keys are never logged or printed
  [green]✓[/green] Keys are isolated from tool execution

[dim]── Tips ──[/dim]

  • Set [cyan]ADAM_VAULT_PASSPHRASE[/cyan] env var to skip password prompts
  • Use [cyan]adam --help[/cyan] to see all commands
"""
    console.print(Panel(welcome_text, border_style="cyan", title="Adam CLI", title_align="left"))


def get_unlocked_vault() -> Vault:
    """Get vault instance, unlocking if needed using session env var."""
    vault = get_vault()
    
    if vault.is_unlocked:
        return vault
    
    # Try to unlock from environment variable
    passphrase = os.environ.get(VAULT_SESSION_ENV)
    if passphrase:
        if vault.unlock(passphrase):
            # Load keys into secure keystore
            load_keys_from_vault(vault)
            return vault
    
    return vault


def unlock_and_load(vault, passphrase: str) -> bool:
    """Unlock vault and load keys into secure keystore."""
    if vault.unlock(passphrase):
        os.environ[VAULT_SESSION_ENV] = passphrase
        # Load all API keys into secure keystore
        loaded = load_keys_from_vault(vault)
        if loaded > 0:
            console.print(f"[dim]Loaded {loaded} API key(s) into secure memory[/dim]")
        return True
    return False


@app.command()
def unlock(
    passphrase: str = typer.Option(
        None,
        "--passphrase", "-p",
        help="Passphrase for non-interactive use (will prompt if not provided)"
    )
):
    """Unlock the vault with passphrase."""
    vault = get_vault()

    if vault.is_unlocked:
        console.print("[yellow]Vault is already unlocked[/yellow]")
        return

    is_new_vault = not vault.vault_exists
    
    # Use provided passphrase or prompt
    if passphrase is None:
        if is_new_vault:
            console.print("\n[bold cyan]🔐 First Time Setup[/bold cyan]")
            console.print("[dim]Create a passphrase to encrypt your secrets.[/dim]\n")
            passphrase = Prompt.ask("Enter new passphrase")
            confirm = Prompt.ask("Confirm passphrase")
            
            if passphrase != confirm:
                console.print("[red]Passphrases do not match[/red]")
                raise typer.Exit(1)
        else:
            passphrase = Prompt.ask("Enter passphrase")

    if unlock_and_load(vault, passphrase):
        if is_new_vault:
            console.print("\n[bold green]✓ Password Set![/bold green]")
            console.print("[bold red]⚠ Don't forget it - it cannot be reset![/bold red]")
            console.print("[dim]Your secrets are encrypted with this passphrase.[/dim]\n")
            print_welcome()
            
            # Ask if they want to set up API keys
            if Confirm.ask("\nWould you like to add an API key now?", default=True):
                setup_api.callback()
        else:
            console.print("[green]✓ Vault unlocked[/green]")
    else:
        console.print("[red]Failed to unlock vault - wrong passphrase?[/red]")
        raise typer.Exit(1)


@app.command()
def lock():
    """Lock the vault and clear secure keystore."""
    vault = get_vault()
    vault.lock()
    keystore.clear()
    os.environ.pop(VAULT_SESSION_ENV, None)
    console.print("[yellow]Vault locked and secure memory cleared[/yellow]")


@app.command()
def add(
    key: str = typer.Argument(..., help="Key name for the secret"),
    value: str = typer.Option(
        None,
        "--value", "-v",
        help="Secret value (will prompt if not provided)"
    ),
    passphrase: str = typer.Option(
        None,
        "--passphrase", "-p",
        help="Vault passphrase (or set ADAM_VAULT_PASSPHRASE env var)"
    ),
    show: bool = typer.Option(
        False,
        "--show",
        help="Show input (don't mask) - useful for SSH/paste issues"
    )
):
    """Add a secret to the vault."""
    vault = get_unlocked_vault()

    if not vault.is_unlocked:
        if passphrase is None:
            passphrase = os.environ.get(VAULT_SESSION_ENV)
        if passphrase is None:
            passphrase = Prompt.ask("Enter vault passphrase")
        
        if not unlock_and_load(vault, passphrase):
            console.print("[red]Failed to unlock vault[/red]")
            raise typer.Exit(1)

    if value is None:
        # Use show flag to determine if we mask input
        if show:
            value = Prompt.ask(f"Enter value for [cyan]{key}[/cyan] (visible)")
        else:
            try:
                value = Prompt.ask(f"Enter value for [cyan]{key}[/cyan]", password=True)
            except EOFError:
                # Fallback if password prompt fails (SSH issues)
                console.print("[yellow]Password prompt failed. Use --show flag:[/yellow]")
                console.print(f"[dim]  adam vault add {key} --show[/dim]")
                raise typer.Exit(1)
    
    vault.set(key, value)
    
    # If this is an API key, also load into secure keystore
    for provider_id, info in API_PROVIDERS.items():
        if key == info["key"]:
            keystore.set(provider_id, value)
            console.print(f"[green]✓ Added secret: {key}[/green]")
            console.print(f"[dim]Loaded into secure memory for {info['name']}[/dim]")
            return
    
    console.print(f"[green]✓ Added secret: {key}[/green]")


@app.command()
def get(
    key: str = typer.Argument(..., help="Key to retrieve"),
    passphrase: str = typer.Option(
        None,
        "--passphrase", "-p",
        help="Vault passphrase (or set ADAM_VAULT_PASSPHRASE env var)"
    )
):
    """Get a secret from the vault."""
    vault = get_unlocked_vault()

    if not vault.is_unlocked:
        if passphrase is None:
            passphrase = os.environ.get(VAULT_SESSION_ENV)
        if passphrase is None:
            passphrase = Prompt.ask("Enter vault passphrase")
        
        if not unlock_and_load(vault, passphrase):
            console.print("[red]Failed to unlock vault[/red]")
            raise typer.Exit(1)

    value = vault.get(key)
    if value:
        # Warn if this looks like an API key
        for provider_id, info in API_PROVIDERS.items():
            if key == info["key"]:
                console.print(f"[yellow]Warning: Showing API key for {info['name']}[/yellow]")
                console.print(f"[dim]Keys should not be shared or logged[/dim]")
                break
        console.print(value)
    else:
        console.print(f"[red]Key '{key}' not found[/red]")
        raise typer.Exit(1)


@app.command()
def delete(
    key: str = typer.Argument(..., help="Key to delete"),
    passphrase: str = typer.Option(
        None,
        "--passphrase", "-p",
        help="Vault passphrase (or set ADAM_VAULT_PASSPHRASE env var)"
    )
):
    """Delete a secret from the vault."""
    vault = get_unlocked_vault()

    if not vault.is_unlocked:
        if passphrase is None:
            passphrase = os.environ.get(VAULT_SESSION_ENV)
        if passphrase is None:
            passphrase = Prompt.ask("Enter vault passphrase")
        
        if not unlock_and_load(vault, passphrase):
            console.print("[red]Failed to unlock vault[/red]")
            raise typer.Exit(1)

    if vault.delete(key):
        # Also clear from secure keystore if it's an API key
        for provider_id, info in API_PROVIDERS.items():
            if key == info["key"]:
                keystore.clear_provider(provider_id)
                break
        console.print(f"[green]✓ Deleted: {key}[/green]")
    else:
        console.print(f"[red]Key '{key}' not found[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_keys(
    passphrase: str = typer.Option(
        None,
        "--passphrase", "-p",
        help="Vault passphrase (or set ADAM_VAULT_PASSPHRASE env var)"
    )
):
    """List all stored keys (not values)."""
    vault = get_unlocked_vault()

    if not vault.is_unlocked:
        if passphrase is None:
            passphrase = os.environ.get(VAULT_SESSION_ENV)
        if passphrase is None:
            passphrase = Prompt.ask("Enter vault passphrase")
        
        if not unlock_and_load(vault, passphrase):
            console.print("[red]Failed to unlock vault[/red]")
            raise typer.Exit(1)

    keys = vault.list_keys()

    if not keys:
        console.print("[yellow]Vault is empty[/yellow]")
        console.print("\n[dim]Use 'adam vault setup-api' to add API keys[/dim]")
        return

    table = Table(title="Vault Keys", show_header=True)
    table.add_column("Key", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Preview", style="yellow")
    
    for k in sorted(keys):
        # Detect key type
        key_type = "secret"
        preview = "****"
        
        for provider_id, info in API_PROVIDERS.items():
            if k == info["key"]:
                key_type = info['name']
                # Show secure preview
                preview = keystore.preview(provider_id, 4) or "****"
                break
        
        table.add_row(k, key_type, preview)
    
    console.print(table)


@app.command("setup-api")
def setup_api():
    """Interactive API key setup for LLM providers."""
    vault = get_unlocked_vault()

    if not vault.is_unlocked:
        passphrase = os.environ.get(VAULT_SESSION_ENV)
        if passphrase is None:
            passphrase = Prompt.ask("Enter vault passphrase")
        
        if not unlock_and_load(vault, passphrase):
            console.print("[red]Failed to unlock vault[/red]")
            raise typer.Exit(1)

    console.print("\n[bold cyan]🔌 API Key Setup[/bold cyan]")
    console.print("[dim]Your keys are encrypted and never exposed to LLMs or tools.[/dim]\n")

    # Show available providers
    table = Table(show_header=True, title="Available LLM Providers")
    table.add_column("#", style="dim", width=3)
    table.add_column("Provider", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Status", style="green")

    provider_list = list(API_PROVIDERS.items())
    for idx, (provider_id, info) in enumerate(provider_list, 1):
        has_key = keystore.has(provider_id)
        status = "✓ Configured" if has_key else "○ Not set"
        status_style = "green" if has_key else "yellow"
        table.add_row(
            str(idx),
            info["name"],
            info["description"],
            f"[{status_style}]{status}[/{status_style}]"
        )
    
    console.print(table)
    console.print()

    # Ask which provider to configure
    choices = [str(i) for i in range(1, len(provider_list) + 1)] + ["0"]
    selection = Prompt.ask(
        "Select provider to configure (0 to finish)",
        choices=choices,
        default="1"
    )

    if selection == "0":
        return

    provider_id, info = provider_list[int(selection) - 1]
    
    console.print(f"\n[bold]{info['name']}[/bold]")
    console.print(f"[dim]{info['description']}[/dim]")
    console.print(f"[dim]Get your API key: {info['url']}[/dim]\n")

    # Try password prompt, fallback to visible input
    console.print("[yellow]Enter API key (input will be hidden):[/yellow]")
    try:
        api_key = Prompt.ask("API key", password=True)
    except EOFError:
        console.print("[yellow]Hidden input failed. Type/paste your key (will be visible):[/yellow]")
        api_key = Prompt.ask("API key (visible)")
    
    if api_key and api_key.strip():
        api_key = api_key.strip()
        # Store in vault (encrypted)
        vault.set(info["key"], api_key)
        # Load into secure keystore
        keystore.set(provider_id, api_key)
        
        console.print(f"[green]✓ {info['name']} API key saved[/green]")
        console.print(f"[dim]Key preview: {keystore.preview(provider_id, 4)}[/dim]")
        console.print("[dim]Key is encrypted and loaded into secure memory[/dim]")
        
        # Check if they want to add more
        if Confirm.ask("\nAdd another provider?", default=False):
            setup_api.callback()
    else:
        console.print("[yellow]Skipped - no key provided[/yellow]")


@app.command("change-passphrase")
def change_passphrase():
    """Change vault passphrase (requires knowing current passphrase)."""
    vault = get_unlocked_vault()

    # First unlock with current passphrase
    if not vault.is_unlocked:
        current = Prompt.ask("Enter current passphrase")
        if not unlock_and_load(vault, current):
            console.print("[red]Incorrect passphrase[/red]")
            raise typer.Exit(1)

    console.print("\n[bold cyan]🔐 Change Passphrase[/bold cyan]")
    new_pass = Prompt.ask("Enter new passphrase")
    confirm = Prompt.ask("Confirm new passphrase")

    if new_pass != confirm:
        console.print("[red]Passphrases do not match[/red]")
        raise typer.Exit(1)

    # To change passphrase, we need to re-encrypt with new key
    # Get all secrets first
    keys = vault.list_keys()
    secrets = {k: vault.get(k) for k in keys}
    
    # Lock and reinitialize with new passphrase
    vault.lock()
    
    # Unlock with new passphrase (this creates new vault)
    if vault.unlock(new_pass):
        # Restore all secrets
        for key, value in secrets.items():
            vault.set(key, value)
        
        # Reload into secure keystore
        os.environ[VAULT_SESSION_ENV] = new_pass
        load_keys_from_vault(vault)
        
        console.print("[green]✓ Passphrase changed successfully[/green]")
    else:
        console.print("[red]Failed to change passphrase[/red]")
        raise typer.Exit(1)


@app.command("status")
def status():
    """Show vault and key status."""
    vault = get_unlocked_vault()  # This now tries to auto-unlock from env var
    
    console.print("\n[bold]Vault Status[/bold]")
    console.print(f"  Unlocked: {'[green]Yes[/green]' if vault.is_unlocked else '[yellow]No[/yellow]'}")
    console.print(f"  Exists: {'[green]Yes[/green]' if vault.vault_exists else '[yellow]No[/yellow]'}")
    
    if vault.is_unlocked:
        keys = vault.list_keys()
        console.print(f"  Keys stored: {len(keys)}")
        
        console.print("\n[bold]Secure Keystore[/bold]")
        providers = keystore.list_providers()
        if providers:
            console.print(f"  Providers loaded: {', '.join(providers)}")
            for p in providers:
                preview = keystore.preview(p, 4)
                console.print(f"    • {p}: {preview}")
        else:
            console.print("  [dim]No API keys loaded[/dim]")
    else:
        passphrase = os.environ.get(VAULT_SESSION_ENV)
        if passphrase:
            console.print("\n[dim]Unlock with: adam vault unlock[/dim]")
        else:
            console.print("\n[dim]Set ADAM_VAULT_PASSPHRASE env var or run: adam vault unlock[/dim]")
