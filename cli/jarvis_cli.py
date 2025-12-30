#!/usr/bin/env python3
"""
Jarvis CLI - Terminal Power User Interface
Clean, efficient command-line interface for all Jarvis capabilities
"""

import click
import requests
import json
import asyncio
import websocket
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm
from typing import Optional, Dict, Any
import os
import sys
from pathlib import Path

# Add paths for imports
sys.path.append('/Volumes/AI_WORKSPACE/CORE/jarvis/modules')
sys.path.append('/Volumes/AI_WORKSPACE')

# Initialize Rich console
console = Console()

# API Configuration
API_BASE = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"

class JarvisTerminal:
    """Main terminal interface handler"""

    def __init__(self):
        self.console = Console()
        self.api_base = API_BASE
        self.ws = None
        self.connected = False

    def connect_websocket(self):
        """Connect to WebSocket for real-time updates"""
        try:
            self.ws = websocket.WebSocket()
            self.ws.connect(WS_URL)
            self.connected = True
            return True
        except Exception as e:
            self.console.print(f"[red]WebSocket connection failed: {e}[/red]")
            return False

    def send_command(self, command: str, context: Dict = None) -> Dict:
        """Send command to API"""
        try:
            response = requests.post(
                f"{self.api_base}/command",
                json={
                    "command": command,
                    "context": context or {},
                    "priority": "normal"
                }
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def trigger_workflow(self, workflow_id: str, params: Dict = None) -> Dict:
        """Trigger n8n workflow"""
        try:
            response = requests.post(
                f"{self.api_base}/workflow/trigger",
                json={
                    "workflow_id": workflow_id,
                    "parameters": params or {}
                }
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def analyze_video(self, url: str) -> Dict:
        """Analyze video content"""
        try:
            response = requests.post(
                f"{self.api_base}/analyze",
                json={
                    "url": url,
                    "analysis_type": "video"
                }
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def search_knowledge(self, query: str) -> Dict:
        """Search knowledge base"""
        try:
            response = requests.get(
                f"{self.api_base}/knowledge/search",
                params={"query": query}
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def get_system_status(self) -> Dict:
        """Get current system status"""
        try:
            response = requests.get(f"{self.api_base}/processes")
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def list_agents(self) -> Dict:
        """List available agents"""
        try:
            response = requests.get(f"{self.api_base}/agents")
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def execute_agent(self, agent: str, task: str, params: Dict = None) -> Dict:
        """Execute specific agent"""
        try:
            response = requests.post(
                f"{self.api_base}/agent/execute",
                json={
                    "agent": agent,
                    "task": task,
                    "parameters": params or {}
                }
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

# Initialize terminal
terminal = JarvisTerminal()

@click.group()
@click.option('--api', default='http://localhost:8000', help='API base URL')
def cli(api):
    """Jarvis Command Center CLI - Your AI workspace at your fingertips"""
    terminal.api_base = api

@cli.command()
@click.argument('command')
@click.option('--context', '-c', help='Additional context as JSON')
@click.option('--priority', '-p', default='normal', type=click.Choice(['normal', 'high', 'urgent']))
def cmd(command, context, priority):
    """Execute a natural language command"""
    console.print(f"[cyan]Executing:[/cyan] {command}")

    ctx = json.loads(context) if context else {}
    result = terminal.send_command(command, ctx)

    if "error" in result:
        console.print(f"[red]Error:[/red] {result['error']}")
    else:
        console.print(Panel(json.dumps(result, indent=2), title="Result"))

@cli.command()
@click.argument('workflow_id')
@click.option('--params', '-p', help='Workflow parameters as JSON')
def workflow(workflow_id, params):
    """Trigger an n8n workflow"""
    console.print(f"[cyan]Triggering workflow:[/cyan] {workflow_id}")

    parameters = json.loads(params) if params else {}
    result = terminal.trigger_workflow(workflow_id, parameters)

    if result.get("status") == "triggered":
        console.print("[green]✓ Workflow triggered successfully[/green]")
    else:
        console.print(f"[red]Failed:[/red] {result}")

@cli.command()
@click.argument('url')
def analyze(url):
    """Analyze video or content from URL"""
    with console.status("[cyan]Analyzing content...[/cyan]") as status:
        result = terminal.analyze_video(url)

    if "analysis" in result:
        analysis = result["analysis"]
        # Create a nice table for results
        table = Table(title="Video Analysis Results")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        if "metadata" in analysis:
            meta = analysis["metadata"]
            table.add_row("Title", meta.get("title", "N/A")[:80])
            table.add_row("Duration", f"{meta.get('duration', 0)} seconds")
            table.add_row("Views", f"{meta.get('view_count', 0):,}")

        console.print(table)

        if "transcript" in analysis:
            console.print("\n[bold]Transcript:[/bold]")
            console.print(analysis["transcript"][:500] + "...")
    else:
        console.print(f"[red]Analysis failed:[/red] {result}")

@cli.command()
@click.argument('query')
def search(query):
    """Search the knowledge base"""
    with console.status("[cyan]Searching knowledge base...[/cyan]"):
        result = terminal.search_knowledge(query)

    if "results" in result:
        console.print(f"\n[green]Found {result['count']} results for '{query}'[/green]\n")
        for item in result["results"][:5]:
            console.print(Panel(
                f"[bold]{item['title']}[/bold]\n\n{item['snippet']}",
                title=item['skill']
            ))
    else:
        console.print(f"[red]Search failed:[/red] {result}")

@cli.command()
def status():
    """Show system status"""
    result = terminal.get_system_status()

    if "processes" in result:
        table = Table(title="Active Processes")
        table.add_column("PID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("CPU %", style="yellow")
        table.add_column("Memory %", style="magenta")

        for proc in result["processes"][:10]:
            table.add_row(
                str(proc["pid"]),
                proc["name"],
                f"{proc['cpu']:.1f}",
                f"{proc['memory']:.1f}"
            )

        console.print(table)
    else:
        console.print("[red]Could not fetch status[/red]")

@cli.command()
def agents():
    """List available agents"""
    result = terminal.list_agents()

    if "agents" in result:
        table = Table(title="Available Agents")
        table.add_column("Agent", style="cyan")
        table.add_column("Capability", style="white")

        for agent, capability in result["agents"].items():
            table.add_row(agent, capability)

        console.print(table)
    else:
        console.print("[red]Could not fetch agents[/red]")

@cli.command()
@click.argument('agent')
@click.argument('task')
@click.option('--params', '-p', help='Agent parameters as JSON')
def agent(agent, task, params):
    """Execute a specific agent"""
    console.print(f"[cyan]Executing {agent} agent...[/cyan]")

    parameters = json.loads(params) if params else {}
    result = terminal.execute_agent(agent, task, parameters)

    if result.get("status") == "executing":
        console.print(f"[green]✓ Agent {agent} started[/green]")
        console.print(f"Task ID: {result.get('task_id')}")
    else:
        console.print(f"[red]Failed:[/red] {result}")

@cli.command()
def interactive():
    """Start interactive mode with live monitoring"""
    console.clear()
    console.print("[bold cyan]Jarvis Command Center - Interactive Mode[/bold cyan]")
    console.print("Type 'help' for commands, 'exit' to quit\n")

    # Connect to WebSocket for live updates
    if terminal.connect_websocket():
        console.print("[green]✓ Connected to live monitoring[/green]\n")

    while True:
        try:
            # Get user input
            command = Prompt.ask("[bold cyan]jarvis>[/bold cyan]")

            if command.lower() == 'exit':
                break
            elif command.lower() == 'help':
                console.print("""
[bold]Available Commands:[/bold]
  analyze <url>     - Analyze video/content
  search <query>    - Search knowledge base
  workflow <id>     - Trigger workflow
  agent <name>      - Execute agent
  status           - Show system status
  agents           - List agents
  clear           - Clear screen
  exit            - Exit interactive mode
                """)
            elif command.lower() == 'clear':
                console.clear()
            elif command.startswith('analyze '):
                url = command.split(' ', 1)[1]
                with console.status("[cyan]Analyzing...[/cyan]"):
                    result = terminal.analyze_video(url)
                console.print(json.dumps(result, indent=2))
            elif command.startswith('search '):
                query = command.split(' ', 1)[1]
                result = terminal.search_knowledge(query)
                if result.get("results"):
                    for r in result["results"][:3]:
                        console.print(f"[cyan]{r['skill']}:[/cyan] {r['snippet']}")
            elif command == 'status':
                result = terminal.get_system_status()
                console.print(json.dumps(result, indent=2))
            else:
                # Send as natural language command
                result = terminal.send_command(command)
                console.print(json.dumps(result, indent=2))

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    console.print("\n[yellow]Goodbye![/yellow]")

@cli.command()
def monitor():
    """Start real-time monitoring dashboard"""
    from rich.live import Live
    from rich.table import Table
    from rich.layout import Layout
    from datetime import datetime
    import time

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )

    layout["header"].update(Panel("[bold cyan]Jarvis Command Center - Live Monitor[/bold cyan]"))
    layout["footer"].update(Panel(f"Press Ctrl+C to exit | Updated: {datetime.now()}"))

    def get_status_table():
        result = terminal.get_system_status()
        table = Table(title="System Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        if "processes" in result:
            table.add_row("Active Processes", str(result["count"]))
            table.add_row("CPU Usage", f"{result.get('cpu', 0):.1f}%")
            table.add_row("Memory Usage", f"{result.get('memory', 0):.1f}%")

        return table

    with Live(layout, refresh_per_second=1, console=console) as live:
        try:
            while True:
                layout["body"].update(get_status_table())
                layout["footer"].update(Panel(f"Press Ctrl+C to exit | Updated: {datetime.now()}"))
                time.sleep(2)
        except KeyboardInterrupt:
            pass

if __name__ == '__main__':
    cli()