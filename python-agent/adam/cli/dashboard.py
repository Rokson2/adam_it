"""Adam Dashboard - Interactive startup interface."""

import os
import sys
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from adam.storage.vault import get_vault
from adam.providers.registry import load_keys_from_vault
from adam.security import keystore

console = Console()

# Same providers as vault.py
PROVIDERS = {
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
    "z-ai": {
        "key": "ZAI_API_KEY",
        "name": "z.ai (GLM)",
        "description": "GLM-4, GLM-4 Plus models",
        "url": "https://open.bigmodel.cn/",
    },
    "z-ai-coding": {
        "key": "ZAI_CODING_API_KEY",
        "name": "z.ai Coding",
        "description": "GLM coding-optimized models",
        "url": "https://open.bigmodel.cn/",
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

# Provider priority for auto-detection
PROVIDER_PRIORITY = ["z-ai-coding", "z-ai", "anthropic", "openai", "openrouter", "deepseek", "ollama"]


def get_default_provider():
    """Get first configured provider by priority."""
    configured = keystore.list_providers()
    for p in PROVIDER_PRIORITY:
        if p in configured:
            return p
    return configured[0] if configured else None


def get_status():
    """Get current status."""
    vault = get_vault()
    passphrase = os.environ.get("ADAM_VAULT_PASSPHRASE")
    
    if passphrase and not vault.is_unlocked and vault.vault_exists:
        vault.unlock(passphrase)
        load_keys_from_vault(vault)
    
    configured = [info["name"] for p, info in PROVIDERS.items() if keystore.has(p)]
    default = get_default_provider()
    
    return {
        "vault_exists": vault.vault_exists,
        "vault_unlocked": vault.is_unlocked,
        "providers": configured,
        "default_provider": default,
    }


def print_logo():
    """Print ASCII logo."""
    logo = """[bold cyan]
   ░███    ░███████      ░███    ░███     ░███             ░██████░██████████
  ░██░██   ░██   ░██    ░██░██   ░████   ░████               ░██      ░██    
 ░██  ░██  ░██    ░██  ░██  ░██  ░██░██ ░██░██               ░██      ░██    
░█████████ ░██    ░██ ░█████████ ░██ ░████ ░██               ░██      ░██    
░██    ░██ ░██    ░██ ░██    ░██ ░██  ░██  ░██               ░██      ░██    
░██    ░██ ░██   ░██  ░██    ░██ ░██       ░██               ░██      ░██    
░██    ░██ ░███████   ░██    ░██ ░██       ░██             ░██████    ░██    
[/bold cyan]
[dim]Your Personal AI Assistant v0.1.0[/dim]
"""
    console.print(logo)


def print_dashboard():
    """Print status dashboard."""
    status = get_status()
    
    # Status
    if status["vault_unlocked"]:
        vstatus = "[green]✓ Unlocked[/green]"
    elif status["vault_exists"]:
        vstatus = "[yellow]○ Locked[/yellow]"
    else:
        vstatus = "[red]○ Not Created[/red]"
    
    pstatus = f"[green]✓ {len(status['providers'])}[/green]" if status["providers"] else "[red]○ None[/red]"
    dprovider = status.get("default_provider", "")
    dname = PROVIDERS.get(dprovider, {}).get("name", dprovider) if dprovider else ""
    
    console.print(Panel(
        f"Vault: {vstatus}\nAPI Keys: {pstatus}\nDefault: {dname or 'none'}",
        title="Status", expand=False
    ))
    
    # Checklist
    t = Table(show_header=False)
    t.add_column("Step")
    t.add_column("Status")
    t.add_column("Action")
    
    if not status["vault_exists"]:
        t.add_row("[red]1.[/red]", "[red]Create vault[/red]", "adam vault unlock")
    elif not status["vault_unlocked"]:
        t.add_row("[yellow]1.[/yellow]", "[yellow]Unlock vault[/yellow]", "adam vault unlock")
    else:
        t.add_row("[green]1.[/green]", "[green]Vault ready[/green]", "")
    
    if not status["providers"]:
        t.add_row("[red]2.[/red]", "[red]Add API key[/red]", "adam vault setup-api")
    else:
        t.add_row("[green]2.[/green]", "[green]API key set[/green]", ", ".join(status["providers"]))
    
    if status["vault_unlocked"] and status["providers"]:
        t.add_row("[green]3.[/green]", "[green]Ready![/green]", "adam agent start")
    else:
        t.add_row("[dim]3.[/dim]", "[dim]Start chat[/dim]", "Complete 1-2 first")
    
    console.print(Panel(t, title="Setup", expand=False))
    
    # Menu
    console.print(Panel(
        "[cyan]1[/cyan]  Unlock vault\n"
        "[cyan]2[/cyan]  Add API key\n"
        "[cyan]3[/cyan]  Start chat\n"
        "[cyan]4[/cyan]  Status\n"
        "[cyan]q[/cyan]  Quit",
        title="Menu", expand=False
    ))
    
    return status


def do_unlock():
    """Unlock vault."""
    vault = get_vault()
    if vault.is_unlocked:
        console.print("[green]Already unlocked[/green]")
        return True
    
    is_new = not vault.vault_exists
    if is_new:
        console.print("\n[cyan]Create a passphrase:[/cyan]")
        p1 = input("New passphrase: ").strip()
        p2 = input("Confirm: ").strip()
        if p1 != p2:
            console.print("[red]Mismatch[/red]")
            return False
        passphrase = p1
    else:
        passphrase = input("Passphrase: ").strip()
    
    if vault.unlock(passphrase):
        os.environ["ADAM_VAULT_PASSPHRASE"] = passphrase
        load_keys_from_vault(vault)
        if is_new:
            console.print("[green]✓ Password set! Don't forget it![/green]")
        else:
            console.print("[green]✓ Unlocked[/green]")
        return True
    
    console.print("[red]Failed[/red]")
    return False


def do_setup_api():
    """Setup API key."""
    vault = get_vault()
    if not vault.is_unlocked:
        console.print("[red]Unlock vault first[/red]")
        return
    
    console.print("\n[cyan]Providers:[/cyan]")
    for i, (pid, info) in enumerate(PROVIDERS.items(), 1):
        status = "✓" if keystore.has(pid) else "○"
        console.print(f"  {i}. {info['name']} - {info.get('description', '')} {status}")
    
    choice = input("\nSelect (1-7): ").strip()
    try:
        pid = list(PROVIDERS.keys())[int(choice) - 1]
    except:
        console.print("[red]Invalid[/red]")
        return
    
    info = PROVIDERS[pid]
    console.print(f"\n[cyan]{info['name']}[/cyan]")
    console.print(f"[dim]Get key: {info['url']}[/dim]")
    
    key = input("Paste API key: ").strip()
    if key:
        vault.set(info["key"], key)
        keystore.set(pid, key)
        console.print(f"[green]✓ Saved[/green]")
    else:
        console.print("[yellow]Skipped[/yellow]")


def run_dashboard():
    """Run interactive dashboard."""
    console.clear()
    print_logo()
    console.print()
    
    status = print_dashboard()
    
    needs_setup = not status["vault_exists"] or not status["vault_unlocked"] or not status["providers"]
    
    if needs_setup:
        console.print()
        if Confirm.ask("\nRun setup?", default=True):
            if not status["vault_exists"] or not status["vault_unlocked"]:
                do_unlock()
            status = get_status()
            if status["vault_unlocked"] and not status["providers"]:
                do_setup_api()
            
            console.clear()
            print_logo()
            console.print()
            status = print_dashboard()
    
    while True:
        console.print()
        default = "3" if status["vault_unlocked"] and status["providers"] else "1"
        choice = input(f"What to do ({default}): ").strip() or default
        
        if choice == "1":
            do_unlock()
        elif choice == "2":
            do_setup_api()
        elif choice == "3":
            if not status["vault_unlocked"]:
                console.print("[red]Unlock first (1)[/red]")
            elif not status["providers"]:
                console.print("[red]Add API key first (2)[/red]")
            else:
                console.print("\n[cyan]Starting chat...[/cyan]\n")
                os.execvp("adam", ["adam", "agent", "start"])
        elif choice == "4":
            vault = get_vault()
            console.print(f"\nVault: {'unlocked' if vault.is_unlocked else 'locked'}")
            console.print(f"Keys: {len(vault.list_keys()) if vault.is_unlocked else 0}")
            console.print(f"Providers: {', '.join(keystore.list_providers())}")
            default_p = get_default_provider()
            if default_p:
                console.print(f"Default: {PROVIDERS.get(default_p, {}).get('name', default_p)}")
        elif choice.lower() == "q":
            console.print("\nBye!")
            raise typer.Exit()
        
        status = get_status()
