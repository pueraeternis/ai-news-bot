# graph/builder.py

import asyncio

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.collector_agent import collect_news
from agents.critic_agent import critique_and_improve_post
from agents.designer_agent import find_image_for_post
from agents.filtering_agent import select_best_news_item
from agents.planner_agent import create_post_plan
from agents.publisher_agent import publish_to_telegram
from agents.translator_agent import translate_post_to_russian
from agents.writer_agent import write_post_from_plan
from core.logging import get_logger
from core.models import AgentState

ERR_FILTERING_FAILED = "Filtering agent failed to select a news item."
ERR_PLANNER_FAILED = "Planner agent failed to create a post plan."
ERR_WRITER_FAILED = "Writer agent failed to write the post."
ERR_TRANSLATOR_FAILED = "Translator agent failed to translate the post."
ERR_CRITIC_FAILED = "Critic agent failed to improve the post."
ERR_PUBLISHER_FAILED = "Publisher agent failed to send the post to Telegram."

logger = get_logger(__name__)


def collector_node(state: AgentState) -> dict:  # noqa: ARG001
    logger.info("--- NODE: COLLECT NEWS ---")
    all_news = collect_news()
    return {"all_news_items": all_news}


def filtering_node(state: AgentState) -> dict:
    logger.info("--- NODE: SELECT BEST NEWS ---")
    selected_item = select_best_news_item(state["all_news_items"])
    if not selected_item:
        raise ValueError(ERR_FILTERING_FAILED)
    return {"selected_news_item": selected_item}


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


def publisher_node(state: AgentState) -> dict:
    logger.info("--- NODE: PUBLISH POST ---")
    success = asyncio.run(
        publish_to_telegram(
            post_text=state["final_post"],
            image_url=state.get("image_url"),
        ),
    )
    if not success:
        raise ValueError(ERR_PUBLISHER_FAILED)
    return {}


def create_graph() -> CompiledStateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("collector", collector_node)
    workflow.add_node("filtering", filtering_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("translator", translator_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("designer", designer_node)
    workflow.add_node("publisher", publisher_node)

    workflow.set_entry_point("collector")
    workflow.add_edge("collector", "filtering")
    workflow.add_edge("filtering", "planner")
    workflow.add_edge("planner", "writer")
    workflow.add_edge("writer", "translator")
    workflow.add_edge("translator", "critic")
    workflow.add_edge("critic", "designer")
    workflow.add_edge("designer", "publisher")
    workflow.add_edge("publisher", END)

    return workflow.compile()
