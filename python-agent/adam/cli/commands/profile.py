"""Profile commands for security profile management."""

import typer
from rich.console import Console
from rich.table import Table
from pathlib import Path
import yaml

app = typer.Typer()
console = Console()

PROFILES_DIR = Path(__file__).parent.parent.parent.parent.parent / "profiles"


@app.command()
def show():
    """Show current profile."""
    # For now, read from config or default
    console.print("[cyan]Current profile: balanced[/cyan]")
    console.print("[dim]Profile switching via runtime coming in Week 6[/dim]")


@app.command()
def set(
    name: str = typer.Argument(..., help="Profile name: paranoid, balanced, permissive"),
):
    """Set the active profile."""
    profile_file = PROFILES_DIR / f"{name}.yaml"
    if not profile_file.exists():
        console.print(f"[red]Profile '{name}' not found[/red]")
        console.print(f"Available: {[f.stem for f in PROFILES_DIR.glob('*.yaml')]}")
        raise typer.Exit(1)

    console.print(f"[green]Profile set to: {name}[/green]")
    console.print("[dim]Note: Requires runtime restart to take effect[/dim]")


@app.command()
def list():
    """List available profiles."""
    table = Table(title="Security Profiles")
    table.add_column("Name")
    table.add_column("Description")

    for profile_path in PROFILES_DIR.glob("*.yaml"):
        try:
            with open(profile_path) as f:
                data = yaml.safe_load(f)
                table.add_row(profile_path.stem, data.get("description", "No description"))
        except:
            table.add_row(profile_path.stem, "Error loading")

    console.print(table)


@app.command()
def info(
    name: str = typer.Argument("balanced", help="Profile name"),
):
    """Show detailed profile information."""
    profile_file = PROFILES_DIR / f"{name}.yaml"
    if not profile_file.exists():
        console.print(f"[red]Profile '{name}' not found[/red]")
        raise typer.Exit(1)

    with open(profile_file) as f:
        data = yaml.safe_load(f)

    console.print(f"\n[bold]{data.get('name', name)}[/bold]")
    console.print(f"[dim]{data.get('description', '')}[/dim]\n")

    # File access
    console.print("[bold]File Access:[/bold]")
    console.print(f"  Read: {data.get('file_access', {}).get('read', [])}")
    console.print(f"  Write: {data.get('file_access', {}).get('write', [])}")
    console.print(f"  Denied: {data.get('file_access', {}).get('denied', [])}")

    # Container
    console.print("\n[bold]Container:[/bold]")
    container = data.get("container", {})
    console.print(f"  Runtime: {container.get('runtime', 'docker')}")
    console.print(f"  Network: {container.get('network', False)}")
    console.print(f"  Memory: {container.get('memory_limit_mb', 0)}MB")
    console.print(f"  Timeout: {container.get('timeout_seconds', 0)}s")
