# core/workflow_progress.py

from __future__ import annotations

from typing import Any

from core.models import NewsItem

_NODE_LABELS: dict[str, str] = {
    "collector": "Collector",
    "filtering": "Filtering",
    "increment_retry": "Retry",
    "duplicate_check": "Duplicate check",
    "planner": "Planner",
    "writer": "Writer (EN)",
    "translator": "Translator (RU)",
    "smm": "SMM",
    "reviewer": "Reviewer",
    "copywriter": "Copywriter",
    "internal_publisher": "Internal publisher",
}


def _out(message: str) -> None:
    print(message, flush=True)


def print_workflow_start() -> None:
    _out("▶ Started\n")


def print_workflow_end(*, success: bool, error: str | None = None) -> None:
    if success:
        _out("✅ Done — check the work group, press Publish to post.\n")
    else:
        _out(f"❌ Failed: {error or 'unknown error'}\n")


def _format_node_result(node: str, update: dict[str, Any]) -> list[str]:
    lines: list[str] = []

    if node == "collector":
        count = len(update.get("all_news_items", []))
        lines.append(f"{count} article(s)")

    elif node == "filtering":
        item: NewsItem | None = update.get("selected_news_item")
        if item:
            lines.append(item.title)
            lines.append(item.source)
        else:
            lines.append("nothing selected")

    elif node == "increment_retry":
        lines.append(f"attempt {update.get('retry_count', '?')}")

    elif node == "duplicate_check":
        lines.append("duplicate" if update.get("is_duplicate") else "unique")

    elif node == "planner":
        plan = update.get("post_plan", "")
        lines.append("ready" if plan else "empty")

    elif node == "writer":
        post = update.get("english_post", "")
        lines.append(f"{len(post)} chars" if post else "empty")

    elif node == "translator":
        post = update.get("russian_post", "")
        lines.append(f"{len(post)} chars" if post else "empty")

    elif node == "smm":
        post = update.get("final_post", "")
        lines.append(f"{len(post)} chars" if post else "empty")

    elif node == "reviewer":
        lines.append("sent for moderation")

    elif node == "copywriter":
        article = update.get("long_read_article", "")
        lines.append(f"{len(article)} chars" if article else "empty")

    elif node == "internal_publisher":
        lines.append(".md sent")

    return lines


def print_node_complete(node: str, update: dict[str, Any]) -> None:
    label = _NODE_LABELS.get(node, node)
    details = _format_node_result(node, update)
    suffix = f" — {', '.join(details)}" if details else ""
    _out(f"● {label}{suffix}")
