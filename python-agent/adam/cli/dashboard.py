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
    logo = r"""
[bold cyan]
     ___    __  __________  ____  ____
    /   |  /  |/  / ___/ _ \/ __ \/  _/
   / /| | / /|_/ / /__/ , _/ /_/ // /  
  / ___ |/ /  / /\___/_/|_|\____/___/  
 /_/  |_/_/  /_/                        
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


def print_main_menu():
    """Print compact main menu for after setup."""
    menu = """
[cyan]Commands[/cyan]
  [yellow]ask[/yellow] "message"    Send a message to Adam
  [yellow]agent start[/yellow]      Start interactive session
  [yellow]vault[/yellow]            Manage secrets & API keys
  [yellow]--help[/yellow]           Show all commands

[dim]Tip: Just type your message after 'adam' to chat![/dim]
"""
    console.print(Panel(menu, title="[bold]Adam CLI[/bold]", border_style="dim"))


def interactive_setup():
    """Run interactive setup flow."""
    from adam.cli.commands.vault import unlock as vault_unlock, setup_api
    
    status = get_status()
    
    # If vault doesn't exist, create it
    if not status["vault_exists"]:
        console.print("\n[bold cyan]Welcome to Adam! Let's get you set up.[/bold cyan]\n")
        console.print("First, create a passphrase to protect your secrets.\n")
        vault_unlock.callback(passphrase=None)
        status = get_status()
    
    # If vault exists but locked, prompt to unlock
    if not status["vault_unlocked"]:
        passphrase = os.environ.get("ADAM_VAULT_PASSPHRASE")
        if passphrase:
            vault = get_vault()
            vault.unlock(passphrase)
            load_keys_from_vault(vault)
        else:
            console.print("\n[yellow]Vault is locked. Enter your passphrase to continue.[/yellow]\n")
            vault_unlock.callback(passphrase=None)
        status = get_status()
    
    # If no API keys, offer to set up
    if status["vault_unlocked"] and not status["providers_configured"]:
        console.print("\n[bold cyan]Now let's add an API key so Adam can respond.[/bold cyan]\n")
        if Confirm.ask("Would you like to add an API key now?", default=True):
            setup_api.callback()


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
            from adam.cli.commands.vault import unlock as vault_unlock
            vault_unlock.callback(passphrase=None)
            status = get_status()
            
        elif choice == "2":
            # Add API key
            from adam.cli.commands.vault import setup_api
            if not status["vault_unlocked"]:
                console.print("[red]Unlock vault first (option 1)[/red]")
            else:
                setup_api.callback()
                status = get_status()
                
        elif choice == "3":
            # Start chat
            if not status["vault_unlocked"]:
                console.print("[red]Unlock vault first (option 1)[/red]")
            elif not status["providers_configured"]:
                console.print("[red]Add an API key first (option 2)[/red]")
            else:
                from adam.cli.commands.agent import start as agent_start
                console.print("\n[bold cyan]Starting chat...[/bold cyan]")
                console.print("[dim]Type 'exit' or Ctrl+D to return to dashboard[/dim]\n")
                agent_start.callback()
                
        elif choice == "4":
            # View settings
            from adam.cli.commands.vault import status as vault_status
            vault_status.callback()
            
        elif choice.lower() == "q":
            console.print("\n[dim]Goodbye![/dim]")
            raise typer.Exit()
            
        else:
            console.print(f"[red]Unknown option: {choice}[/red]")
        
        # Refresh status after actions
        status = get_status()
