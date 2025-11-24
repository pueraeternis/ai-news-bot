# graph/builder.py

import asyncio
from typing import Literal

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.collector_agent import collect_news
from agents.copywriter_agent import write_long_read_article
from agents.filtering_agent import select_best_news_item
from agents.internal_publisher_agent import send_article_file
from agents.planner_agent import create_post_plan
from agents.reviewer_agent import send_for_review
from agents.smm_agent import critique_and_improve_post
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
ERR_SMM_FAILED = "SMM agent failed to improve the post."
ERR_COPYWRITER_FAILED = "Copywriter agent failed to write the article."
ERR_INTERNAL_PUB_FAILED = "Internal publisher failed to send the file."
ERR_REVIEW_FAILED = "Reviewer agent failed to send post for review."

MAX_CANDIDATES_FOR_LLM = 30
MAX_GLOBAL_RETRIES = 10

logger = get_logger(__name__)


def collector_node(state: AgentState) -> dict:
    """
    Collect news from a randomly selected rubric.
    """
    logger.info("--- NODE: COLLECT NEWS ---")

    current_retries = state.get("retry_count", 0)
    all_news = collect_news()

    return {
        "all_news_items": all_news,
        "excluded_urls": state.get("excluded_urls", []),
        "retry_count": current_retries,
    }


def filtering_node(state: AgentState) -> dict:
    logger.info("--- NODE: SELECT BEST NEWS ---")

    all_items = state["all_news_items"]

    if not all_items:
        logger.warning("Collector found no news in this rubric.")
        return {"selected_news_item": None}

    exclude_urls = state.get("excluded_urls", [])

    candidate_items = [item for item in all_items if str(item.url) not in exclude_urls]
    top_candidates = candidate_items[:MAX_CANDIDATES_FOR_LLM]

    logger.info("Selected top %d candidates for LLM review.", len(top_candidates))

    selected_item = select_best_news_item(news_items=top_candidates)

    if not selected_item:
        logger.info("Filtering agent rejected all candidates or found none.")
        return {"selected_news_item": None}

    text_to_embed = f"{selected_item.title}\n{selected_item.summary}"
    return {"selected_news_item": selected_item, "text_to_embed": text_to_embed}


def should_continue_collection(state: AgentState) -> Literal["continue", "retry_rubric", "end"]:
    """
    Decide whether to proceed, try another rubric, or give up.
    """
    if state.get("selected_news_item"):
        return "continue"

    current_retries = state.get("retry_count", 0)

    if current_retries < MAX_GLOBAL_RETRIES:
        logger.info("No suitable news found. Switching rubric (Attempt %d/%d).", current_retries + 1, MAX_GLOBAL_RETRIES)
        return "retry_rubric"

    logger.error("Failed to find any suitable news after %d rubric changes. Giving up.", MAX_GLOBAL_RETRIES)
    return "end"


def duplicate_check_node(state: AgentState) -> dict:
    logger.info("--- NODE: DUPLICATE CHECK ---")
    storage = VectorStorage()
    is_duplicate = storage.is_duplicate(state["text_to_embed"])

    if is_duplicate:
        current_excluded = state["excluded_urls"]
        new_excluded = [*current_excluded, str(state["selected_news_item"].url)]
        return {"is_duplicate": True, "excluded_urls": new_excluded}

    return {"is_duplicate": False}


def should_continue_after_duplicate(state: AgentState) -> Literal["planner", "retry_rubric"]:
    if state["is_duplicate"]:
        logger.info("Duplicate detected. Will try another rubric/selection.")
        return "retry_rubric"

    logger.info("News is unique. Proceeding to planning.")
    return "planner"


def increment_retry_node(state: AgentState) -> dict:
    return {"retry_count": state["retry_count"] + 1}


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


# --- BRANCH 1: SMM ---


def smm_node(state: AgentState) -> dict:
    logger.info("--- NODE: SMM AGENT ---")
    final_post = critique_and_improve_post(state["russian_post"])
    if not final_post:
        raise ValueError(ERR_SMM_FAILED)
    return {"final_post": final_post}


def reviewer_node(state: AgentState) -> dict:
    """Node for sending the post to admin for review AND saving to storage."""
    logger.info("--- NODE: SEND FOR REVIEW ---")

    # Send to the work chat with buttons
    success = asyncio.run(
        send_for_review(
            post_text=state["final_post"],
            news_title=state["selected_news_item"].title,
            source_url=str(state["selected_news_item"].url),
        ),
    )

    if not success:
        raise ValueError(ERR_REVIEW_FAILED)

    # Immediately save to the database (the news item is considered processed)
    logger.info("Saving processed article to vector storage (pre-publication).")
    storage = VectorStorage()
    selected_item: NewsItem = state["selected_news_item"]
    storage.add_article(
        article_id=str(selected_item.url),
        text_to_embed=state["text_to_embed"],
        metadata={"title": selected_item.title, "source": selected_item.source},
    )

    return {}


# --- BRANCH 2: LONG READ ---


def copywriter_node(state: AgentState) -> dict:
    logger.info("--- NODE: COPYWRITER (LONG READ) ---")
    # Use the Russian translation as the basis for the long read
    article_text = write_long_read_article(state["russian_post"])
    if not article_text:
        raise ValueError(ERR_COPYWRITER_FAILED)
    return {"long_read_article": article_text}


def internal_publisher_node(state: AgentState) -> dict:
    logger.info("--- NODE: INTERNAL PUBLISH (FILE) ---")
    success = asyncio.run(
        send_article_file(
            article_text=state["long_read_article"],
            topic=state["selected_news_item"].title,
        ),
    )
    if not success:
        # Do not fail the whole graph if the file was not sent, since the main post might have already been published
        logger.error(ERR_INTERNAL_PUB_FAILED)
    return {}


def create_graph() -> CompiledStateGraph:
    workflow = StateGraph(AgentState)

    # Nodes
    workflow.add_node("collector", collector_node)
    workflow.add_node("filtering", filtering_node)
    workflow.add_node("increment_retry", increment_retry_node)
    workflow.add_node("duplicate_check", duplicate_check_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("translator", translator_node)

    # SMM Branch
    workflow.add_node("smm", smm_node)
    workflow.add_node("reviewer", reviewer_node)

    # Long Read Branch
    workflow.add_node("copywriter", copywriter_node)
    workflow.add_node("internal_publisher", internal_publisher_node)

    # Edges
    workflow.set_entry_point("collector")
    workflow.add_edge("collector", "filtering")

    workflow.add_conditional_edges(
        "filtering",
        should_continue_collection,
        {"continue": "duplicate_check", "retry_rubric": "increment_retry", "end": END},
    )
    workflow.add_edge("increment_retry", "collector")

    workflow.add_conditional_edges(
        "duplicate_check",
        should_continue_after_duplicate,
        {"planner": "planner", "retry_rubric": "increment_retry"},
    )

    workflow.add_edge("planner", "writer")
    workflow.add_edge("writer", "translator")

    # --- BRANCHING POINT ---
    # After the translator, the graph splits into TWO branches
    workflow.add_edge("translator", "smm")
    workflow.add_edge("translator", "copywriter")

    # End of SMM branch
    workflow.add_edge("smm", "reviewer")
    workflow.add_edge("reviewer", END)

    # End of Long Read branch
    workflow.add_edge("copywriter", "internal_publisher")
    workflow.add_edge("internal_publisher", END)

    return workflow.compile()
