# core/workflow_progress.py

from __future__ import annotations

from typing import Any

from core.models import NewsItem

_PREVIEW_LEN = 160

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


def _preview(text: str, max_len: int = _PREVIEW_LEN) -> str:
    clean = " ".join(text.split())
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 1] + "…"


def _out(message: str) -> None:
    print(message, flush=True)


def print_workflow_start() -> None:
    _out("\n▶ Workflow started\n")


def print_workflow_end(*, success: bool, error: str | None = None) -> None:
    if success:
        _out("\n✅ Workflow finished — post sent to the work group for review.")
        _out("   Press Publish in Telegram to post to the channel.\n")
    else:
        _out(f"\n❌ Workflow failed: {error or 'unknown error'}\n")


def _format_node_result(node: str, update: dict[str, Any]) -> list[str]:
    lines: list[str] = []

    if node == "collector":
        count = len(update.get("all_news_items", []))
        lines.append(f"{count} fresh article(s) collected")

    elif node == "filtering":
        item: NewsItem | None = update.get("selected_news_item")
        if item:
            lines.append(f"selected: {_preview(item.title, 100)}")
            lines.append(f"source: {item.source}")
        else:
            lines.append("no suitable article in this rubric")

    elif node == "increment_retry":
        attempt = update.get("retry_count", "?")
        lines.append(f"switching rubric (attempt {attempt})")

    elif node == "duplicate_check":
        if update.get("is_duplicate"):
            lines.append("duplicate found — will try another article/rubric")
        else:
            lines.append("article is unique")

    elif node == "planner":
        plan = update.get("post_plan", "")
        if plan:
            lines.append(f"plan ready ({len(plan)} chars)")
            lines.append(_preview(plan))

    elif node == "writer":
        post = update.get("english_post", "")
        if post:
            lines.append(f"English post ({len(post)} chars)")
            lines.append(_preview(post))

    elif node == "translator":
        post = update.get("russian_post", "")
        if post:
            lines.append(f"Russian post ({len(post)} chars)")
            lines.append(_preview(post))

    elif node == "smm":
        post = update.get("final_post", "")
        if post:
            lines.append(f"polished post ({len(post)} chars)")
            lines.append(_preview(post))

    elif node == "reviewer":
        lines.append("post sent to work group with Publish / Reject buttons")

    elif node == "copywriter":
        article = update.get("long_read_article", "")
        if article:
            lines.append(f"long-read article ({len(article)} chars)")

    elif node == "internal_publisher":
        lines.append("long-read .md file sent to work group")

    return lines


def print_node_complete(node: str, update: dict[str, Any]) -> None:
    label = _NODE_LABELS.get(node, node)
    _out(f"● {label}")

    for line in _format_node_result(node, update):
        _out(f"  {line}")

    _out("")
