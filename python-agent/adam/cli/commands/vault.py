"""Vault commands for secret management."""

import os
import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from adam.storage.vault import Vault, VaultLockedError, get_vault

app = typer.Typer()
console = Console()

# Environment variable for session passphrase
VAULT_SESSION_ENV = "ADAM_VAULT_PASSPHRASE"


def get_unlocked_vault() -> Vault:
    """Get vault instance, unlocking if needed using session env var."""
    vault = get_vault()
    
    if vault.is_unlocked:
        return vault
    
    # Try to unlock from environment variable
    passphrase = os.environ.get(VAULT_SESSION_ENV)
    if passphrase:
        if vault.unlock(passphrase):
            return vault
    
    return vault


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

    # Use provided passphrase or prompt
    if passphrase is None:
        passphrase = Prompt.ask("Enter passphrase", password=True)

    if not vault.vault_exists:
        if passphrase is None:
            confirm = Prompt.ask("Create new vault? Confirm passphrase", password=True)
            if passphrase != confirm:
                console.print("[red]Passphrases do not match[/red]")
                raise typer.Exit(1)
        else:
            console.print("[yellow]Creating new vault...[/yellow]")

    if vault.unlock(passphrase):
        # Set session env var for this shell (won't persist but helps with chained commands)
        os.environ[VAULT_SESSION_ENV] = passphrase
        console.print("[green]Vault unlocked[/green]")
        console.print("[dim]Tip: Set ADAM_VAULT_PASSPHRASE env var for non-interactive use[/dim]")
    else:
        console.print("[red]Failed to unlock vault - wrong passphrase?[/red]")
        raise typer.Exit(1)


@app.command()
def lock():
    """Lock the vault."""
    vault = get_vault()
    vault.lock()
    # Clear session env var
    os.environ.pop(VAULT_SESSION_ENV, None)
    console.print("[yellow]Vault locked[/yellow]")


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
    )
):
    """Add a secret to the vault."""
    vault = get_unlocked_vault()

    if not vault.is_unlocked:
        if passphrase is None:
            passphrase = os.environ.get(VAULT_SESSION_ENV)
        if passphrase is None:
            passphrase = Prompt.ask("Enter vault passphrase", password=True)
        
        if not vault.unlock(passphrase):
            console.print("[red]Failed to unlock vault[/red]")
            raise typer.Exit(1)

    if value is None:
        value = Prompt.ask(f"Enter value for [cyan]{key}[/cyan]", password=True)
    
    vault.set(key, value)
    console.print(f"[green]Added secret: {key}[/green]")


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
            passphrase = Prompt.ask("Enter vault passphrase", password=True)
        
        if not vault.unlock(passphrase):
            console.print("[red]Failed to unlock vault[/red]")
            raise typer.Exit(1)

    value = vault.get(key)
    if value:
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
            passphrase = Prompt.ask("Enter vault passphrase", password=True)
        
        if not vault.unlock(passphrase):
            console.print("[red]Failed to unlock vault[/red]")
            raise typer.Exit(1)

    if vault.delete(key):
        console.print(f"[green]Deleted: {key}[/green]")
    else:
        console.print(f"[red]Key '{key}' not found[/red]")
        raise typer.Exit(1)


@app.command()
def list(
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
            passphrase = Prompt.ask("Enter vault passphrase", password=True)
        
        if not vault.unlock(passphrase):
            console.print("[red]Failed to unlock vault[/red]")
            raise typer.Exit(1)

    keys = vault.list_keys()

    if not keys:
        console.print("[yellow]Vault is empty[/yellow]")
        return

    table = Table(title="Vault Keys")
    table.add_column("Key")
    for k in keys:
        table.add_row(k)
    console.print(table)
