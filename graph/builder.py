# graph/builder.py

import asyncio
from typing import Literal

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.collector_agent import collect_news
from agents.critic_agent import critique_and_improve_post
from agents.designer_agent import find_image_for_post
from agents.filtering_agent import select_best_news_item
from agents.planner_agent import create_post_plan
from agents.publisher_agent import publish_to_telegram
from agents.summarizer_agent import summarize_for_caption
from agents.translator_agent import translate_post_to_russian
from agents.writer_agent import write_post_from_plan
from core.logging import get_logger
from core.models import AgentState, NewsItem
from core.storage import VectorStorage

ERR_FILTERING_FAILED = "Filtering agent failed to select any news item after exclusions."
ERR_DUPLICATE_FOUND = "Duplicate article found."
ERR_PLANNER_FAILED = "Planner agent failed to create a post plan."
ERR_WRITER_FAILED = "Writer agent failed to write the post."
ERR_TRANSLATOR_FAILED = "Translator agent failed to translate the post."
ERR_CRITIC_FAILED = "Critic agent failed to improve the post."
ERR_PUBLISHER_FAILED = "Publisher agent failed to send the post to Telegram."
ERR_SUMMARIZER_FAILED = "Failed to summarize text."


TELEGRAM_CAPTION_LIMIT = 900
INITIAL_SUMMARY_TOKENS = 900
TOKEN_DECREMENT = 100
MIN_SUMMARY_TOKENS = 150
MAX_CANDIDATES_FOR_LLM = 50

logger = get_logger(__name__)


def collector_node(state: AgentState) -> dict:  # noqa: ARG001
    logger.info("--- NODE: COLLECT NEWS ---")
    all_news = collect_news()
    return {"all_news_items": all_news, "excluded_urls": []}


def filtering_node(state: AgentState) -> dict:
    logger.info("--- NODE: SELECT BEST NEWS ---")

    all_items = state["all_news_items"]
    exclude_urls = state.get("excluded_urls", [])

    candidate_items = [item for item in all_items if str(item.url) not in exclude_urls]
    top_candidates = candidate_items[:MAX_CANDIDATES_FOR_LLM]

    logger.info("Selected top %d candidates for LLM review.", len(top_candidates))

    selected_item = select_best_news_item(news_items=top_candidates)

    if not selected_item:
        raise ValueError(ERR_FILTERING_FAILED)

    text_to_embed = f"{selected_item.title}\n{selected_item.summary}"
    return {"selected_news_item": selected_item, "text_to_embed": text_to_embed}


def duplicate_check_node(state: AgentState) -> dict:
    logger.info("--- NODE: DUPLICATE CHECK ---")
    storage = VectorStorage()
    is_duplicate = storage.is_duplicate(state["text_to_embed"])

    if is_duplicate:
        current_excluded = state["excluded_urls"]
        new_excluded = [*current_excluded, str(state["selected_news_item"].url)]
        return {"is_duplicate": True, "excluded_urls": new_excluded}

    return {"is_duplicate": False}


def should_continue_node(state: AgentState) -> Literal["continue", "retry"]:
    """Determine the next step based on the duplication check."""
    if state["is_duplicate"]:
        logger.info("Duplicate detected. Retrying with a new selection.")
        return "retry"

    logger.info("News is unique. Proceeding to planning.")
    return "continue"


def planner_node(state: AgentState) -> dict:
    logger.info("--- NODE: CREATE POST PLAN ---")
    plan = create_post_plan(state["selected_news_item"])
    if not plan:
        raise ValueError(ERR_PLANNER_FAILED)
    return {"post_plan": plan}


def writer_node(state: AgentState) -> dict:
    logger.info("--- NODE: WRITE POST (EN) ---")
    english_post = write_post_from_plan(
        post_plan=state["post_plan"],
        source_url=str(state["selected_news_item"].url),
    )
    if not english_post:
        raise ValueError(ERR_WRITER_FAILED)
    return {"english_post": english_post}


def translator_node(state: AgentState) -> dict:
    logger.info("--- NODE: TRANSLATE POST (RU) ---")
    russian_post = translate_post_to_russian(state["english_post"])
    if not russian_post:
        raise ValueError(ERR_TRANSLATOR_FAILED)
    return {"russian_post": russian_post}


def critic_node(state: AgentState) -> dict:
    logger.info("--- NODE: CRITIQUE AND IMPROVE POST ---")
    final_post = critique_and_improve_post(state["russian_post"])
    if not final_post:
        raise ValueError(ERR_CRITIC_FAILED)
    return {"final_post": final_post}


def designer_node(state: AgentState) -> dict:
    """Node for finding a suitable image for the post."""
    logger.info("--- NODE: FIND IMAGE ---")
    image_url = find_image_for_post(
        news_item=state["selected_news_item"],
        post_text=state["final_post"],
    )
    return {"image_url": image_url}


def prepare_publication_node(state: AgentState) -> dict:
    logger.info("--- NODE: PREPARE PUBLICATION ---")
    final_post = state["final_post"]
    image_url = state.get("image_url")

    current_tokens = state.get("summarizer_max_tokens")
    if current_tokens is None:
        current_tokens = INITIAL_SUMMARY_TOKENS

    publication_text = final_post
    if image_url and len(final_post) > TELEGRAM_CAPTION_LIMIT:
        publication_text = summarize_for_caption(final_post, current_tokens)

    return {
        "publication_text": publication_text,
        "summarizer_max_tokens": current_tokens - TOKEN_DECREMENT,
    }


def publisher_node(state: AgentState) -> dict:
    logger.info("--- NODE: PUBLISH POST ---")
    success = asyncio.run(
        publish_to_telegram(
            post_text=state["publication_text"],
            image_url=state.get("image_url"),
        ),
    )

    if success:
        logger.info("Saving published article to vector storage.")
        storage = VectorStorage()
        selected_item: NewsItem = state["selected_news_item"]
        storage.add_article(
            article_id=str(selected_item.url),
            text_to_embed=state["text_to_embed"],
            metadata={"title": selected_item.title, "source": selected_item.source},
        )

    return {"publication_status": "success" if success else "fail"}


def should_retry_publication_node(state: AgentState) -> Literal["end", "retry_summary"]:
    if state["publication_status"] == "success":
        return "end"

    if state["summarizer_max_tokens"] < MIN_SUMMARY_TOKENS:
        logger.error("Failed to summarize text to required length. Aborting.")
        raise ValueError(ERR_SUMMARIZER_FAILED)

    logger.warning("Publication failed. Retrying with fewer tokens.")
    return "retry_summary"


def create_graph() -> CompiledStateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("collector", collector_node)
    workflow.add_node("filtering", filtering_node)
    workflow.add_node("duplicate_check", duplicate_check_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("translator", translator_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("designer", designer_node)
    workflow.add_node("prepare_publication", prepare_publication_node)
    workflow.add_node("publisher", publisher_node)

    workflow.set_entry_point("collector")
    workflow.add_edge("collector", "filtering")
    workflow.add_edge("filtering", "duplicate_check")

    workflow.add_conditional_edges(
        "duplicate_check",
        should_continue_node,
        {"continue": "planner", "retry": "filtering"},
    )

    workflow.add_edge("planner", "writer")
    workflow.add_edge("writer", "translator")
    workflow.add_edge("translator", "critic")
    workflow.add_edge("critic", "designer")

    workflow.add_edge("designer", "prepare_publication")
    workflow.add_edge("prepare_publication", "publisher")

    workflow.add_conditional_edges(
        "publisher",
        should_retry_publication_node,
        {"end": END, "retry_summary": "prepare_publication"},
    )

    return workflow.compile()
