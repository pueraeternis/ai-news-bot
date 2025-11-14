# main.py

import click
from rich import print as rich_print

from agents.collector_agent import collect_news
from agents.filtering_agent import select_best_news_item
from agents.planner_agent import create_post_plan
from core.logging import setup_logging


@click.group()
def cli() -> None:
    """AI News Bot CLI."""


@cli.command()
def process() -> None:
    """Run the full pipeline: news collection, selection of the best item, and post plan creation."""
    setup_logging()

    click.echo("Step 1: Collecting news...")
    news_items = collect_news()

    if not news_items:
        click.echo("No news found. Check logs for details.")
        return

    click.echo(f"Collection complete. Retrieved {len(news_items)} items.")

    click.echo("\nStep 2: Selecting the best news item via LLM...")
    best_item = select_best_news_item(news_items)

    if not best_item:
        click.echo("Failed to select the best news item. Check logs for details.")
        return

    click.echo("\nSelected the best news item:")
    rich_print(best_item)

    click.echo("\nStep 3: Generating post plan...")
    post_plan = create_post_plan(best_item)

    if post_plan:
        click.echo("\nGenerated post plan:")
        rich_print(post_plan)
    else:
        click.echo("Failed to generate post plan. Check logs for details.")


if __name__ == "__main__":
    cli()
