# main.py

import click
from rich.console import Console
from rich.markdown import Markdown

from agents.collector_agent import collect_news
from agents.filtering_agent import select_best_news_item
from agents.planner_agent import create_post_plan
from agents.translator_agent import translate_post_to_russian
from agents.writer_agent import write_post_from_plan
from core.logging import setup_logging

console = Console()


@click.group()
def cli() -> None:
    """AI News Bot CLI."""


@cli.command()
def process() -> None:
    """Run the full pipeline: collection, selection, planning, writing, and translation."""
    setup_logging()

    click.echo("Step 1: Collecting news...")
    news_items = collect_news()
    if not news_items:
        click.echo("No news found.")
        return
    click.echo(f"Collection complete. Retrieved {len(news_items)} items.")

    click.echo("\nStep 2: Selecting the best news item...")
    best_item = select_best_news_item(news_items)
    if not best_item:
        click.echo("Failed to select the best news item.")
        return
    click.echo(f"Selected news item: '{best_item.title}'")

    click.echo("\nStep 3: Generating post plan...")
    post_plan = create_post_plan(best_item)
    if not post_plan:
        click.echo("Failed to generate post plan.")
        return
    click.echo("Post plan successfully created.")

    click.echo("\nStep 4: Writing the post in English...")
    english_post = write_post_from_plan(post_plan)
    if not english_post:
        click.echo("Failed to write the post.")
        return
    click.echo("English post successfully written.")

    click.echo("\nStep 5: Translating post to Russian...")
    russian_post = translate_post_to_russian(english_post)

    if russian_post:
        click.echo("\n--- FINAL TELEGRAM POST (RUSSIAN) ---")
        markdown = Markdown(russian_post)
        console.print(markdown)
        click.echo("--- END OF POST ---")
    else:
        click.echo("Failed to translate the post.")


if __name__ == "__main__":
    cli()
