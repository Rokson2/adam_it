"""Vault commands for secret management."""

import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from adam.storage import Vault, VaultLockedError

app = typer.Typer()
console = Console()


def get_vault() -> Vault:
    """Get vault instance."""
    return Vault()


@app.command()
def unlock():
    """Unlock the vault with passphrase."""
    vault = get_vault()

    if vault.is_unlocked:
        console.print("[yellow]Vault is already unlocked[/yellow]")
        return

    passphrase = Prompt.ask("Enter passphrase", password=True)

    if not vault.vault_exists:
        confirm = Prompt.ask("Create new vault? Confirm passphrase", password=True)
        if passphrase != confirm:
            console.print("[red]Passphrases do not match[/red]")
            raise typer.Exit(1)

    if vault.unlock(passphrase):
        console.print("[green]Vault unlocked[/green]")
    else:
        console.print("[red]Failed to unlock vault - wrong passphrase?[/red]")
        raise typer.Exit(1)


@app.command()
def lock():
    """Lock the vault."""
    vault = get_vault()
    vault.lock()
    console.print("[yellow]Vault locked[/yellow]")


@app.command()
def add(
    key: str = typer.Argument(..., help="Key name for the secret"),
):
    """Add a secret to the vault."""
    vault = get_vault()

    if not vault.is_unlocked:
        console.print("[red]Vault is locked. Run 'adam vault unlock' first[/red]")
        raise typer.Exit(1)

    value = Prompt.ask(f"Enter value for [cyan]{key}[/cyan]", password=True)
    vault.set(key, value)
    console.print(f"[green]Added secret: {key}[/green]")


@app.command()
def get(
    key: str = typer.Argument(..., help="Key to retrieve"),
):
    """Get a secret from the vault."""
    vault = get_vault()

    if not vault.is_unlocked:
        console.print("[red]Vault is locked. Run 'adam vault unlock' first[/red]")
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
):
    """Delete a secret from the vault."""
    vault = get_vault()

    if not vault.is_unlocked:
        console.print("[red]Vault is locked. Run 'adam vault unlock' first[/red]")
        raise typer.Exit(1)

    if vault.delete(key):
        console.print(f"[green]Deleted: {key}[/green]")
    else:
        console.print(f"[red]Key '{key}' not found[/red]")
        raise typer.Exit(1)


@app.command()
def list():
    """List all stored keys (not values)."""
    vault = get_vault()

    if not vault.is_unlocked:
        console.print("[red]Vault is locked. Run 'adam vault unlock' first[/red]")
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
