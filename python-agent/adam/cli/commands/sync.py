"""Sync commands for export/import."""

import typer
from rich.console import Console
from pathlib import Path
import tarfile
import json
from datetime import datetime

app = typer.Typer()
console = Console()

ADAM_DIR = Path.home() / ".adam"


@app.command()
def export(
    output: Path = typer.Option(None, "--output", "-o", help="Output file path"),
    include_vault: bool = typer.Option(False, "--include-vault", help="Include encrypted vault"),
):
    """Export Adam data for backup or transfer."""
    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = Path.cwd() / f"adam-export-{timestamp}.tar.gz"

    if not ADAM_DIR.exists():
        console.print("[yellow]No Adam data found to export[/yellow]")
        raise typer.Exit(0)

    with tarfile.open(output, "w:gz") as tar:
        for item in ADAM_DIR.iterdir():
            if item.name == "vault" and not include_vault:
                console.print("[dim]Skipping vault (use --include-vault)[/dim]")
                continue
            tar.add(item, arcname=item.name)

    console.print(f"[green]Exported to: {output}[/green]")


@app.command(name="import")
def import_data(
    input_file: Path = typer.Argument(..., help="Export file to import"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing data"),
):
    """Import Adam data from backup."""
    if not ADAM_DIR.exists():
        ADAM_DIR.mkdir(parents=True)

    if any(ADAM_DIR.iterdir()) and not overwrite:
        console.print("[yellow]Adam data already exists. Use --overwrite to replace.[/yellow]")
        raise typer.Exit(1)

    with tarfile.open(input_file, "r:gz") as tar:
        tar.extractall(ADAM_DIR)

    console.print(f"[green]Imported from: {input_file}[/green]")
