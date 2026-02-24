"""Model management commands."""

import typer
from rich.console import Console
from rich.table import Table

from adam.providers.models import get_model_registry

app = typer.Typer()
console = Console()


@app.command("list")
def list_models(
    provider: str = typer.Option(None, "-p", "--provider", help="Filter by provider"),
    all: bool = typer.Option(False, "--all", "-a", help="Show deprecated models too"),
):
    """List available models."""
    registry = get_model_registry()
    models = registry.list_models(provider)
    
    if not all:
        models = [m for m in models if not m.deprecated]
    
    if not models:
        console.print("[yellow]No models found[/yellow]")
        return
    
    table = Table(title="Available Models")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Provider")
    table.add_column("Context")
    table.add_column("Features")
    
    for m in models:
        features = []
        if m.supports_vision:
            features.append("👁")
        if m.supports_tools:
            features.append("🔧")
        
        status = "[dim]" if m.deprecated else ""
        end = "[/dim]" if m.deprecated else ""
        
        table.add_row(
            f"{status}{m.id}{end}",
            f"{status}{m.name}{end}",
            f"{status}{m.provider}{end}",
            f"{status}{m.context_length // 1024}K{end}",
            " ".join(features) if not m.deprecated else ""
        )
    
    console.print(table)
    console.print(f"\n[dim]{len(models)} models[/dim]")


@app.command("providers")
def list_providers():
    """List available providers."""
    registry = get_model_registry()
    providers = registry.list_providers()
    
    console.print("\n[bold]Available Providers:[/bold]\n")
    
    for p in providers:
        default = registry.get_default(p)
        console.print(f"  • [cyan]{p}[/cyan] (default: {default})")
    
    console.print()


@app.command("update")
def update_models():
    """Check for model updates from providers."""
    import asyncio
    
    registry = get_model_registry()
    
    console.print("[cyan]Checking for model updates...[/cyan]")
    
    try:
        result = asyncio.run(registry.check_for_updates())
        
        if result["new_models"]:
            console.print(f"[green]Found {len(result['new_models'])} new models:[/green]")
            for m in result["new_models"]:
                console.print(f"  • {m}")
        else:
            console.print("[green]Models are up to date[/green]")
        
        if result["errors"]:
            console.print(f"[yellow]Some errors occurred:[/yellow]")
            for e in result["errors"]:
                console.print(f"  • {e}")
                
    except Exception as e:
        console.print(f"[red]Update failed: {e}[/red]")


@app.command("info")
def model_info(model_id: str):
    """Show details about a specific model."""
    registry = get_model_registry()
    model = registry.get(model_id)
    
    if not model:
        console.print(f"[red]Model not found: {model_id}[/red]")
        raise typer.Exit(1)
    
    console.print(f"\n[bold cyan]{model.name}[/bold cyan]")
    console.print(f"ID: {model.id}")
    console.print(f"Provider: {model.provider}")
    console.print(f"Context: {model.context_length // 1024}K tokens")
    console.print(f"Description: {model.description}")
    
    features = []
    if model.supports_vision:
        features.append("Vision")
    if model.supports_tools:
        features.append("Tools")
    
    if features:
        console.print(f"Features: {', '.join(features)}")
    
    if model.deprecated:
        console.print("[yellow]⚠ This model is deprecated[/yellow]")
    
    console.print()


@app.command("defaults")
def show_defaults():
    """Show default models for each provider."""
    from adam.providers.models.registry import PROVIDER_DEFAULTS
    
    console.print("\n[bold]Provider Defaults:[/bold]\n")
    
    table = Table()
    table.add_column("Provider", style="cyan")
    table.add_column("Default Model")
    
    for provider, model in PROVIDER_DEFAULTS.items():
        table.add_row(provider, model)
    
    console.print(table)
    console.print()
