"""
Adam Dashboard - Interactive startup interface.
"""

import os
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.layout import Layout
from rich.align import Align
from rich import box

from adam.storage.vault import get_vault
from adam.providers.registry import load_keys_from_vault
from adam.security import keystore

console = Console()

# Supported providers for setup checklist
PROVIDERS = {
    "anthropic": {"name": "Anthropic (Claude)", "key": "ANTHROPIC_API_KEY"},
    "openai": {"name": "OpenAI (GPT-4)", "key": "OPENAI_API_KEY"},
    "openrouter": {"name": "OpenRouter", "key": "OPENROUTER_API_KEY"},
    "z-ai": {"name": "z.ai", "key": "ZAI_API_KEY"},
    "deepseek": {"name": "DeepSeek", "key": "DEEPSEEK_API_KEY"},
}


def get_status():
    """Get current system status."""
    vault = get_vault()
    
    # Try to auto-unlock from env var
    passphrase = os.environ.get("ADAM_VAULT_PASSPHRASE")
    if passphrase and not vault.is_unlocked and vault.vault_exists:
        if vault.unlock(passphrase):
            load_keys_from_vault(vault)
    
    status = {
        "vault_exists": vault.vault_exists,
        "vault_unlocked": vault.is_unlocked,
        "has_passphrase": bool(passphrase),
        "providers_configured": [],
        "providers_missing": [],
    }
    
    # Check which providers are configured
    for provider_id, info in PROVIDERS.items():
        if keystore.has(provider_id):
            status["providers_configured"].append(info["name"])
        else:
            status["providers_missing"].append(info["name"])
    
    return status


def print_logo():
    """Print Adam ASCII logo."""
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


def print_status_dashboard():
    """Print the main status dashboard."""
    status = get_status()
    
    # Status indicators
    if status["vault_unlocked"]:
        vault_status = "[green]✓ Unlocked[/green]"
    elif status["vault_exists"]:
        vault_status = "[yellow]○ Locked[/yellow]"
    else:
        vault_status = "[red]○ Not Created[/red]"
    
    if status["providers_configured"]:
        count = len(status["providers_configured"])
        providers_status = f"[green]✓ {count} configured[/green]"
    else:
        providers_status = "[red]○ None configured[/red]"
    
    # Status panel
    status_text = f"""
[dim]System Status[/dim]

  Vault:          {vault_status}
  API Providers:  {providers_status}
"""
    
    console.print(Panel(status_text, title="[bold]Status[/bold]", border_style="dim", expand=False))
    
    # Setup checklist
    checklist_items = []
    
    # Step 1: Vault
    if not status["vault_exists"]:
        checklist_items.append(("[red]1.[/red]", "[red]Create vault[/red]", "Run: [cyan]adam vault unlock[/cyan]"))
    elif not status["vault_unlocked"]:
        checklist_items.append(("[yellow]1.[/yellow]", "[yellow]Unlock vault[/yellow]", "Run: [cyan]adam vault unlock[/cyan]"))
    else:
        checklist_items.append(("[green]1.[/green]", "[green]Vault ready[/green]", ""))
    
    # Step 2: API Keys
    if not status["providers_configured"]:
        checklist_items.append(("[red]2.[/red]", "[red]Add API key[/red]", "Run: [cyan]adam vault setup-api[/cyan]"))
    else:
        providers_list = ", ".join(status["providers_configured"])
        checklist_items.append(("[green]2.[/green]", "[green]API key configured[/green]", f"[dim]{providers_list}[/dim]"))
    
    # Step 3: Ready to chat
    if status["vault_unlocked"] and status["providers_configured"]:
        checklist_items.append(("[green]3.[/green]", "[green]Ready to chat![/green]", 'Run: [cyan]adam agent start[/cyan] or [cyan]adam ask "..."[/cyan]'))
    else:
        checklist_items.append(("[dim]3.[/dim]", "[dim]Start chatting[/dim]", "Complete steps 1-2 first"))
    
    # Checklist table
    checklist_table = Table(show_header=False, box=None, padding=(0, 2))
    checklist_table.add_column("Step", width=4)
    checklist_table.add_column("Status", width=20)
    checklist_table.add_column("Action")
    
    for step, status_msg, action in checklist_items:
        checklist_table.add_row(step, status_msg, action)
    
    console.print(Panel(checklist_table, title="[bold]Setup Checklist[/bold]", border_style="dim", expand=False))
    
    # Quick actions
    actions_text = """
[dim]Quick Actions[/dim]

  [cyan]1[/cyan]  Unlock vault / Setup passphrase
  [cyan]2[/cyan]  Add API key
  [cyan]3[/cyan]  Start chat
  [cyan]4[/cyan]  View settings
  [cyan]q[/cyan]  Quit
"""
    console.print(Panel(actions_text, title="[bold]Menu[/bold]", border_style="dim", expand=False))
    
    return status


def do_vault_unlock():
    """Perform vault unlock with interactive prompts."""
    from adam.storage.vault import get_vault
    from adam.providers.registry import load_keys_from_vault
    
    vault = get_vault()
    
    if vault.is_unlocked:
        console.print("[yellow]Vault is already unlocked[/yellow]")
        return True
    
    is_new_vault = not vault.vault_exists
    
    if is_new_vault:
        passphrase = Prompt.ask("Enter new passphrase", password=True)
        confirm = Prompt.ask("Confirm passphrase", password=True)
        
        if passphrase != confirm:
            console.print("[red]Passphrases do not match[/red]")
            return False
    else:
        passphrase = Prompt.ask("Enter passphrase", password=True)
    
    if vault.unlock(passphrase):
        os.environ["ADAM_VAULT_PASSPHRASE"] = passphrase
        load_keys_from_vault(vault)
        
        if is_new_vault:
            console.print("\n[bold green]✓ Password Set![/bold green]")
            console.print("[bold red]⚠ Don't forget it - it cannot be reset![/bold red]")
            console.print("[dim]Your secrets are encrypted with this passphrase.[/dim]\n")
        else:
            console.print("[green]✓ Vault unlocked[/green]")
        return True
    else:
        console.print("[red]Failed to unlock vault - wrong passphrase?[/red]")
        return False


def do_setup_api():
    """Perform API key setup with interactive prompts."""
    from adam.cli.commands.vault import API_PROVIDERS
    
    vault = get_vault()
    
    if not vault.is_unlocked:
        console.print("[red]Vault is locked. Unlock first.[/red]")
        return False
    
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
    
    choices = [str(i) for i in range(1, len(provider_list) + 1)] + ["0"]
    selection = Prompt.ask(
        "Select provider to configure (0 to finish)",
        choices=choices,
        default="1"
    )
    
    if selection == "0":
        return True
    
    provider_id, info = provider_list[int(selection) - 1]
    
    console.print(f"\n[bold]{info['name']}[/bold]")
    console.print(f"[dim]{info['description']}[/dim]")
    console.print(f"[dim]Get your API key: {info['url']}[/dim]\n")
    
    api_key = Prompt.ask("Enter API key (leave empty to skip)", password=True)
    
    if api_key:
        vault.set(info["key"], api_key)
        keystore.set(provider_id, api_key)
        console.print(f"[green]✓ {info['name']} API key saved[/green]")
        console.print(f"[dim]Key preview: {keystore.preview(provider_id, 4)}[/dim]")
        return True
    else:
        console.print("[yellow]Skipped - no key provided[/yellow]")
        return False


def interactive_setup():
    """Run interactive setup flow."""
    status = get_status()
    
    # If vault doesn't exist, create it
    if not status["vault_exists"]:
        console.print("\n[bold cyan]Welcome to Adam! Let's get you set up.[/bold cyan]\n")
        console.print("First, create a passphrase to protect your secrets.\n")
        if not do_vault_unlock():
            return
        status = get_status()
    
    # If vault exists but locked, prompt to unlock
    if not status["vault_unlocked"]:
        console.print("\n[yellow]Vault is locked. Enter your passphrase to continue.[/yellow]\n")
        if not do_vault_unlock():
            return
        status = get_status()
    
    # If no API keys, offer to set up
    if status["vault_unlocked"] and not status["providers_configured"]:
        console.print("\n[bold cyan]Now let's add an API key so Adam can respond.[/bold cyan]\n")
        if Confirm.ask("Would you like to add an API key now?", default=True):
            do_setup_api()


def run_dashboard():
    """Run the interactive dashboard."""
    console.clear()
    print_logo()
    console.print()
    
    status = print_status_dashboard()
    
    # Check if setup is needed
    needs_setup = (
        not status["vault_exists"] or
        not status["vault_unlocked"] or
        not status["providers_configured"]
    )
    
    if needs_setup:
        console.print()
        if Confirm.ask("\nWould you like to run setup?", default=True):
            interactive_setup()
            console.clear()
            print_logo()
            console.print()
            status = print_status_dashboard()
    
    # Main menu loop
    while True:
        console.print()
        if status["vault_unlocked"] and status["providers_configured"]:
            default_choice = "3"
        else:
            default_choice = "1"
        
        choice = Prompt.ask("What would you like to do?", default=default_choice)
        
        if choice == "1":
            # Unlock vault
            do_vault_unlock()
            status = get_status()
            
        elif choice == "2":
            # Add API key
            if not status["vault_unlocked"]:
                console.print("[red]Unlock vault first (option 1)[/red]")
            else:
                do_setup_api()
                status = get_status()
                
        elif choice == "3":
            # Start chat
            if not status["vault_unlocked"]:
                console.print("[red]Unlock vault first (option 1)[/red]")
            elif not status["providers_configured"]:
                console.print("[red]Add an API key first (option 2)[/red]")
            else:
                console.print("\n[bold cyan]Starting chat...[/bold cyan]")
                console.print("[dim]Type 'exit' or Ctrl+D to return to dashboard[/dim]\n")
                # Import and call agent start
                import subprocess
                subprocess.run(["adam", "agent", "start"])
                
        elif choice == "4":
            # View settings
            vault = get_vault()
            console.print("\n[bold]Vault Status[/bold]")
            console.print(f"  Unlocked: {'[green]Yes[/green]' if vault.is_unlocked else '[yellow]No[/yellow]'}")
            console.print(f"  Exists: {'[green]Yes[/green]' if vault.vault_exists else '[yellow]No[/yellow]'}")
            
            if vault.is_unlocked:
                keys = vault.list_keys()
                console.print(f"  Keys stored: {len(keys)}")
                
                console.print("\n[bold]Secure Keystore[/bold]")
                providers = keystore.list_providers()
                if providers:
                    for p in providers:
                        preview = keystore.preview(p, 4)
                        console.print(f"  • {p}: {preview}")
                else:
                    console.print("  [dim]No API keys loaded[/dim]")
            
        elif choice.lower() == "q":
            console.print("\n[dim]Goodbye![/dim]")
            raise typer.Exit()
            
        else:
            console.print(f"[red]Unknown option: {choice}[/red]")
        
        # Refresh status after actions
        status = get_status()
