"""Vault commands for secret management."""

import os
import sys
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from adam.storage.vault import Vault, get_vault
from adam.providers.registry import load_keys_from_vault
from adam.security import keystore

app = typer.Typer()
console = Console()

VAULT_SESSION_ENV = "ADAM_VAULT_PASSPHRASE"

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
        "description": "Access to 100+ models",
        "url": "https://openrouter.ai/keys",
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
        "description": "Run models locally",
        "url": "http://localhost:11434",
    },
}


def get_unlocked_vault() -> Vault:
    """Get vault instance, auto-unlock from env var if possible."""
    vault = get_vault()
    if vault.is_unlocked:
        return vault
    passphrase = os.environ.get(VAULT_SESSION_ENV)
    if passphrase and vault.vault_exists:
        if vault.unlock(passphrase):
            load_keys_from_vault(vault)
    return vault


def ensure_unlocked(vault) -> bool:
    """Ensure vault is unlocked, prompt if needed."""
    if vault.is_unlocked:
        return True
    passphrase = os.environ.get(VAULT_SESSION_ENV)
    if not passphrase:
        passphrase = Prompt.ask("Enter passphrase")
    if vault.unlock(passphrase):
        os.environ[VAULT_SESSION_ENV] = passphrase
        load_keys_from_vault(vault)
        return True
    return False


@app.command()
def unlock(
    passphrase: str = typer.Option(None, "-p", "--passphrase"),
):
    """Unlock vault with passphrase."""
    vault = get_vault()
    if vault.is_unlocked:
        console.print("[green]Already unlocked[/green]")
        return
    
    is_new = not vault.vault_exists
    if not passphrase:
        if is_new:
            console.print("\n[cyan]First time setup - create a passphrase[/cyan]\n")
            passphrase = Prompt.ask("New passphrase")
            confirm = Prompt.ask("Confirm")
            if passphrase != confirm:
                console.print("[red]Mismatch[/red]")
                raise typer.Exit(1)
        else:
            passphrase = Prompt.ask("Passphrase")
    
    if vault.unlock(passphrase):
        os.environ[VAULT_SESSION_ENV] = passphrase
        load_keys_from_vault(vault)
        if is_new:
            console.print("\n[green]✓ Password set! Don't forget it![/green]\n")
        else:
            console.print("[green]✓ Unlocked[/green]")
    else:
        console.print("[red]Failed[/red]")
        raise typer.Exit(1)


@app.command()
def lock():
    """Lock vault."""
    get_vault().lock()
    keystore.clear()
    os.environ.pop(VAULT_SESSION_ENV, None)
    console.print("[yellow]Locked[/yellow]")


@app.command()
def add(
    key: str = typer.Argument(..., help="Key name"),
    value: str = typer.Option(None, "-v", "--value", help="Value (skip prompt)"),
):
    """Add a secret. Use -v to avoid prompt."""
    vault = get_unlocked_vault()
    if not ensure_unlocked(vault):
        console.print("[red]Unlock first[/red]")
        raise typer.Exit(1)
    
    if not value:
        # Simple input - no masking (works in SSH)
        console.print(f"[cyan]Enter value for {key}:[/cyan]")
        try:
            value = input().strip()
        except EOFError:
            console.print("[red]No input received. Use: adam vault add KEY -v VALUE[/red]")
            raise typer.Exit(1)
    
    if not value:
        console.print("[red]Empty value[/red]")
        raise typer.Exit(1)
    
    vault.set(key, value)
    
    # Load into keystore if API key
    for pid, info in API_PROVIDERS.items():
        if key == info["key"]:
            keystore.set(pid, value)
            console.print(f"[green]✓ Saved {key} ({info['name']})[/green]")
            return
    
    console.print(f"[green]✓ Saved {key}[/green]")


@app.command()
def get(
    key: str = typer.Argument(...),
):
    """Get a secret."""
    vault = get_unlocked_vault()
    if not ensure_unlocked(vault):
        raise typer.Exit(1)
    
    value = vault.get(key)
    if value:
        console.print(value)
    else:
        console.print(f"[red]Not found: {key}[/red]")
        raise typer.Exit(1)


@app.command()
def delete(key: str = typer.Argument(...)):
    """Delete a secret."""
    vault = get_unlocked_vault()
    if not ensure_unlocked(vault):
        raise typer.Exit(1)
    
    if vault.delete(key):
        console.print(f"[green]✓ Deleted {key}[/green]")
    else:
        console.print(f"[red]Not found[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_cmd():
    """List all keys."""
    vault = get_unlocked_vault()
    if not ensure_unlocked(vault):
        raise typer.Exit(1)
    
    keys = vault.list_keys()
    if not keys:
        console.print("[yellow]Empty[/yellow]")
        return
    
    t = Table(title="Keys")
    t.add_column("Key")
    t.add_column("Type")
    for k in sorted(keys):
        ktype = "secret"
        for pid, info in API_PROVIDERS.items():
            if k == info["key"]:
                ktype = info["name"]
                break
        t.add_row(k, ktype)
    console.print(t)


@app.command("setup-api")
def setup_api(
    provider: str = typer.Option(None, "-p", "--provider", help="Provider name"),
    key: str = typer.Option(None, "-k", "--key", help="API key (skip prompt)"),
):
    """Setup API key for LLM provider.
    
    Examples:
      adam vault setup-api                    # Interactive
      adam vault setup-api -p anthropic       # Select provider
      adam vault setup-api -p anthropic -k sk-ant-xxx   # Non-interactive
    """
    vault = get_unlocked_vault()
    if not ensure_unlocked(vault):
        raise typer.Exit(1)
    
    # Show providers
    console.print("\n[cyan]Available Providers:[/cyan]\n")
    t = Table()
    t.add_column("#")
    t.add_column("Provider")
    t.add_column("Status")
    
    plist = list(API_PROVIDERS.items())
    for i, (pid, info) in enumerate(plist, 1):
        status = "[green]✓[/green]" if keystore.has(pid) else "[dim]○[/dim]"
        t.add_row(str(i), info["name"], status)
    console.print(t)
    
    # Select provider
    if not provider:
        console.print()
        choice = Prompt.ask("Select provider (1-5)", default="1")
        try:
            provider = plist[int(choice) - 1][0]
        except (ValueError, IndexError):
            console.print("[red]Invalid choice[/red]")
            raise typer.Exit(1)
    
    if provider not in API_PROVIDERS:
        console.print(f"[red]Unknown: {provider}[/red]")
        raise typer.Exit(1)
    
    info = API_PROVIDERS[provider]
    console.print(f"\n[cyan]{info['name']}[/cyan]")
    console.print(f"[dim]Get key: {info['url']}[/dim]")
    
    # Get API key
    if not key:
        console.print(f"\n[cyan]Paste your API key:[/cyan]")
        try:
            key = input().strip()
        except EOFError:
            console.print("[red]No input. Use: adam vault setup-api -p PROVIDER -k YOUR_KEY[/red]")
            raise typer.Exit(1)
    
    if not key:
        console.print("[red]Empty key[/red]")
        raise typer.Exit(1)
    
    # Save
    vault.set(info["key"], key)
    keystore.set(provider, key)
    
    preview = key[:8] + "..." if len(key) > 8 else key
    console.print(f"[green]✓ Saved {info['name']} key ({preview})[/green]")


@app.command("status")
def status_cmd():
    """Show vault status."""
    vault = get_unlocked_vault()
    console.print(f"\nVault: {'[green]Unlocked[/green]' if vault.is_unlocked else '[yellow]Locked[/yellow]'}")
    
    if vault.is_unlocked:
        keys = vault.list_keys()
        console.print(f"Keys: {len(keys)}")
        
        providers = keystore.list_providers()
        if providers:
            console.print(f"\nAPI Keys loaded: {', '.join(providers)}")
