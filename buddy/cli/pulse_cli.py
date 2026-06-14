"""
PULSE CLI — `buddy pulse` sub-commands.

buddy pulse start          — Start the PULSE web server
buddy pulse create         — Interactively create a PULSE employee
buddy pulse kt             — Run a KT session from the CLI
buddy pulse status         — Show employee status
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Force UTF-8 output so emojis don't crash on Windows CP1252 terminals
os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

pulse_app = typer.Typer(
    name="pulse",
    help="PULSE -- Virtual Employee's ERA. Manage and interact with your virtual team member.",
    no_args_is_help=True,
)
console = Console(highlight=False)


# ---------------------------------------------------------------------------
# buddy pulse start
# ---------------------------------------------------------------------------


@pulse_app.command("start")
def start(
    host: str = typer.Option("localhost", "--host", "-H", help="Host to bind to"),
    port: int = typer.Option(8888, "--port", "-p", help="Port to listen on"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser automatically"),
) -> None:
    """Start the PULSE web server (API + UI)."""
    try:
        from buddy.pulse.app import PulseApp
    except ImportError:
        console.print("[red]PULSE module not available. Make sure buddy-ai is properly installed.[/red]")
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            f"[bold blue]>> Starting PULSE[/bold blue]\n" f"[dim]http://{host}:{port}[/dim]",
            border_style="blue",
        )
    )
    app = PulseApp(host=host, port=port, open_browser=not no_browser)
    app.serve()


# ---------------------------------------------------------------------------
# buddy pulse create
# ---------------------------------------------------------------------------


@pulse_app.command("create")
def create(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Employee full name"),
    role: Optional[str] = typer.Option(None, "--role", "-r", help="Job role/title"),
    department: str = typer.Option("Engineering", "--department", "-d"),
    model: str = typer.Option("gpt-4o", "--model", "-m", help="LLM model to use"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save config to JSON file"),
) -> None:
    """Interactively create a PULSE employee configuration."""
    console.print(Panel.fit("[bold blue]>> Create a PULSE Employee[/bold blue]", border_style="blue"))

    if not name:
        name = typer.prompt("Employee full name")
    if not role:
        role = typer.prompt("Job role/title")
    skills_raw = typer.prompt("Skills (comma-separated)", default="")
    skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
    timezone = typer.prompt("Timezone", default="UTC")
    company = typer.prompt("Company name", default="")
    reporting_to = typer.prompt("Reports to (manager name)", default="")

    config = {
        "employee_profile": {
            "full_name": name,
            "role": role,
            "department": department,
            "skills": skills,
            "timezone": timezone,
            "company_name": company or None,
            "reporting_to": reporting_to or None,
        },
        "model_provider": "openai",
        "model_id": model,
    }

    console.print("\n[bold green]✅ Employee configuration:[/bold green]")
    console.print_json(json.dumps(config, indent=2))

    if output:
        output.write_text(json.dumps(config, indent=2))
        console.print(f"\n[dim]Saved to {output}[/dim]")
    else:
        console.print("\n[dim]Pass --output <file.json> to save this configuration.[/dim]")


# ---------------------------------------------------------------------------
# buddy pulse kt
# ---------------------------------------------------------------------------


@pulse_app.command("kt")
def run_kt(
    source: str = typer.Argument(..., help="File path, URL, or text to learn from"),
    session_name: str = typer.Option(..., "--session", "-s", help="KT session name"),
    knowledge_giver: str = typer.Option("Unknown", "--from", "-f", help="Who provided this knowledge"),
    model: str = typer.Option("gpt-4o", "--model", "-m"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save KT summary to JSON"),
) -> None:
    """Run a document/URL KT session from the CLI."""
    try:
        from buddy.models.openai import OpenAIChat
        from buddy.pulse import EmployeeProfile, KTSourceType, PulseEmployee
    except ImportError as e:
        console.print(f"[red]Import error: {e}[/red]")
        raise typer.Exit(1)

    console.print(f"[blue]📚 Starting KT: {session_name}[/blue]")
    console.print(f"[dim]Source: {source[:80]}...[/dim]" if len(source) > 80 else f"[dim]Source: {source}[/dim]")

    emp = PulseEmployee(
        employee_profile=EmployeeProfile(full_name="CLI Employee", role="Analyst"),
        model=OpenAIChat(id=model),
    )

    # Detect source type
    source_type = KTSourceType.URL if source.startswith("http") else KTSourceType.DOCUMENT

    with console.status("[blue]Processing KT...[/blue]"):
        summary = emp.take_kt(
            source=source,
            source_type=source_type,
            session_name=session_name,
            knowledge_giver=knowledge_giver,
        )

    console.print("\n[bold green]✅ KT Complete[/bold green]")
    console.print(
        Panel(
            (
                f"[bold]Confidence:[/bold] {summary.confidence_score:.0%}\n\n"
                f"[bold]Mental Model:[/bold]\n{summary.mental_model}\n\n"
                f"[bold]Key Concepts:[/bold] {', '.join(summary.key_concepts[:5])}\n\n"
                f"[bold]Open Questions:[/bold]\n" + "\n".join(f"  • {q}" for q in summary.open_questions[:3])
                if summary.open_questions
                else "[dim]None[/dim]"
            ),
            title=f"KT Summary — {summary.session_name}",
            border_style="green",
        )
    )

    if output:
        output.write_text(json.dumps(summary.model_dump(), indent=2, default=str))
        console.print(f"\n[dim]Summary saved to {output}[/dim]")


# ---------------------------------------------------------------------------
# buddy pulse status
# ---------------------------------------------------------------------------


@pulse_app.command("status")
def status() -> None:
    """Show PULSE module status and available features."""
    try:
        from buddy.pulse import __all__ as pulse_exports

        available = True
        export_count = len(pulse_exports)
    except ImportError:
        available = False
        export_count = 0

    table = Table(title="PULSE Module Status", show_header=True, header_style="bold blue")
    table.add_column("Component", style="cyan")
    table.add_column("Status")

    components = [
        ("PulseEmployee", "buddy.pulse.employee"),
        ("KT Engine", "buddy.pulse.kt"),
        ("Meeting Intelligence", "buddy.pulse.meeting"),
        ("Work Engine", "buddy.pulse.work"),
        ("Communication Hub", "buddy.pulse.comms"),
        ("Professional Memory", "buddy.pulse.memory"),
        ("Feedback System", "buddy.pulse.feedback"),
        ("Onboarding Workflow", "buddy.pulse.onboarding"),
        ("FastAPI Router", "buddy.pulse.router"),
        ("Web App", "buddy.pulse.app"),
    ]

    for comp_name, module_path in components:
        try:
            __import__(module_path)
            table.add_row(comp_name, "[green]✅ Available[/green]")
        except ImportError as e:
            table.add_row(comp_name, f"[red]❌ {e}[/red]")

    console.print(table)
    if available:
        console.print(f"\n[green]PULSE is fully operational — {export_count} exports available.[/green]")
    else:
        console.print("\n[red]PULSE module has import errors. Check your installation.[/red]")
