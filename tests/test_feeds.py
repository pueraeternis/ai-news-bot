# tests/test_feeds.py

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import feedparser
import requests
from rich.console import Console
from rich.table import Table

# Configuration
SOURCES_FILE = Path("/home/v.babchuk/projects/ai_news_bot/data/sources.json")
REQUEST_TIMEOUT = 15
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"),
}

console = Console()


def load_feeds() -> list[dict[str, Any]]:
    """Load and validate RSS feed sources from JSON file."""
    console.print(f"Reading sources from: [cyan]{SOURCES_FILE}[/cyan]\n", style="bold")

    if not SOURCES_FILE.exists():
        console.print(f"Error: File not found: {SOURCES_FILE}", style="bold red")
        return []

    try:
        with SOURCES_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            feeds = data.get("rss_feeds", [])
            console.print(f"Found {len(feeds)} feed(s) to check.\n")
            return feeds
    except json.JSONDecodeError as e:
        console.print(f"Error: Invalid JSON in sources file: {e}", style="bold red")
        return []
    except Exception as e:
        console.print(f"Error: Unexpected error reading file: {e}", style="bold red")
        return []


def check_single_feed(feed_info: dict[str, Any], index: int, total: int) -> str:
    """Check a single RSS feed and return status: 'success', 'empty', or 'failed'."""
    name = feed_info.get("name", "Unnamed Feed")
    url = feed_info.get("url")

    console.print(f"({index}/{total}) Checking '[bold cyan]{name}[/bold cyan]' → {url}")

    if not url or not isinstance(url, str):
        console.print("   [bold red]Failed: Missing or invalid URL[/bold red]")
        return "failed"

    try:
        # Step 1: Check HTTP accessibility
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        # Step 2: Parse as RSS/Atom feed
        feed = feedparser.parse(response.content)

        if feed.bozo:
            reason = str(getattr(feed, "bozo_exception", "Unknown parsing error"))
            console.print(f"   [bold red]Failed: Invalid RSS/Atom format[/bold red] → {reason}")
            return "failed"

        # Step 3: Check for entries
        if not feed.entries:
            console.print("   [yellow]Warning: Valid feed, but empty (no entries)[/yellow]")
            return "empty"

        console.print("   [bold green]Success: Valid and contains entries[/bold green]")
        return "success"

    except requests.exceptions.Timeout:
        console.print("   [bold red]Failed: Request timed out[/bold red]")
        return "failed"
    except requests.exceptions.ConnectionError:
        console.print("   [bold red]Failed: Could not connect to host[/bold red]")
        return "failed"
    except requests.exceptions.HTTPError as e:
        console.print(f"   [bold red]Failed: HTTP error {e.response.status_code}[/bold red]")
        return "failed"
    except Exception as e:
        console.print(f"   [bold red]Failed: Unexpected error[/bold red] → {e}")
        return "failed"


def print_summary(results: list[dict[str, Any]]) -> None:
    """Display a clean summary table of results."""
    total = len(results)
    success = sum(1 for r in results if r["status"] == "success")
    empty = sum(1 for r in results if r["status"] == "empty")
    failed = sum(1 for r in results if r["status"] == "failed")

    table = Table(title="\n[bold]Final Report[/bold]", show_header=True, header_style="bold magenta")
    table.add_column("Status", style="dim")
    table.add_column("Count", justify="right")
    table.add_column("Description")

    table.add_row("Total", str(total), "All feeds checked")
    table.add_row("Success", f"[green]{success}[/green]", "Valid feeds with entries")
    if empty:
        table.add_row("Empty", f"[yellow]{empty}[/yellow]", "Valid but no posts")
    table.add_row("Failed", f"[red]{failed}[/red]", "Inaccessible or invalid")

    console.print(table)

    if failed == 0 and empty == 0:
        console.print("\n[bold green]All feeds are healthy and up to date![/bold green]")
    elif failed == 0:
        console.print("\n[bold yellow]All feeds are accessible. Some are empty.[/bold yellow]")
    else:
        console.print(f"\n[bold red]{failed} feed(s) have issues. Check above.[/bold red]")


def main() -> None:
    feeds = load_feeds()
    if not feeds:
        return

    console.print("-" * 60)

    results = []
    for i, feed in enumerate(feeds, start=1):
        status = check_single_feed(feed, i, len(feeds))
        results.append({"name": feed.get("name", "N/A"), "url": feed.get("url"), "status": status})
        console.print()  # empty line for readability

    print_summary(results)


if __name__ == "__main__":
    main()
