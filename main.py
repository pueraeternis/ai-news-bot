# main.py

import click
from rich import print as rich_print

from agents.collector_agent import collect_news
from core.logging import setup_logging


@click.group()
def cli() -> None:
    """AI News Bot CLI."""


@cli.command()
def collect() -> None:
    """Launch the news collector agent and output the results to the console."""
    # 1. Set up logging. All logs will be written to a file.
    setup_logging()

    # 2. Launch the main function of our agent
    click.echo("Starting news collection...")
    news_items = collect_news()

    # 3. Output the result to the console
    if news_items:
        click.echo(f"Successfully collected {len(news_items)} news items. Showing the first 5:")
        # Use rich.print for nicely formatted output of Pydantic models
        for item in news_items[:5]:
            rich_print(item)
    else:
        click.echo("No news items were collected. Check logs for details.")


if __name__ == "__main__":
    cli()
