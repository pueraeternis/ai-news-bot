# graph_builder.py


from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.collector_agent import collect_news
from agents.filtering_agent import select_best_news_item
from agents.planner_agent import create_post_plan
from agents.publisher_agent import publish_to_telegram
from agents.translator_agent import translate_post_to_russian
from agents.writer_agent import write_post_from_plan
from core.logging import get_logger
from core.models import AgentState

# Error messages
ERR_FILTERING_FAILED = "Filtering agent failed to select a news item."
ERR_PLANNER_FAILED = "Planner agent failed to create a post plan."
ERR_WRITER_FAILED = "Writer agent failed to write the post."
ERR_TRANSLATOR_FAILED = "Translator agent failed to translate the post."
ERR_PUBLISHER_FAILED = "Publisher agent failed to send the post to Telegram."

logger = get_logger(__name__)


def collector_node(state: AgentState) -> dict:  # noqa: ARG001
    """Node for collecting news."""
    logger.info("--- NODE: COLLECT NEWS ---")
    all_news = collect_news()
    return {"all_news_items": all_news}


def filtering_node(state: AgentState) -> dict:
    """Node for selecting the best news item."""
    logger.info("--- NODE: SELECT BEST NEWS ---")
    selected_item = select_best_news_item(state["all_news_items"])
    if not selected_item:
        raise ValueError(ERR_FILTERING_FAILED)
    return {"selected_news_item": selected_item}


def planner_node(state: AgentState) -> dict:
    """Node for creating a post plan."""
    logger.info("--- NODE: CREATE POST PLAN ---")
    plan = create_post_plan(state["selected_news_item"])
    if not plan:
        raise ValueError(ERR_PLANNER_FAILED)
    return {"post_plan": plan}


def writer_node(state: AgentState) -> dict:
    """Node for writing the post in English."""
    logger.info("--- NODE: WRITE POST (EN) ---")
    english_post = write_post_from_plan(state["post_plan"])
    if not english_post:
        raise ValueError(ERR_WRITER_FAILED)
    return {"english_post": english_post}


def translator_node(state: AgentState) -> dict:
    """Node for translating the post to Russian."""
    logger.info("--- NODE: TRANSLATE POST (RU) ---")
    russian_post = translate_post_to_russian(state["english_post"])
    if not russian_post:
        raise ValueError(ERR_TRANSLATOR_FAILED)
    return {"russian_post": russian_post}


def publisher_node(state: AgentState) -> dict:
    """Node for publishing the post to Telegram."""
    logger.info("--- NODE: PUBLISH POST ---")
    success = publish_to_telegram(state["russian_post"])
    if not success:
        raise ValueError(ERR_PUBLISHER_FAILED)
    # This node does not add anything to the state; it performs an action
    return {}


def create_graph() -> CompiledStateGraph:
    """Create and compiles a LangGraph, defining the workflow."""
    workflow = StateGraph(AgentState)

    # Add nodes to the graph
    workflow.add_node("collector", collector_node)
    workflow.add_node("filtering", filtering_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("translator", translator_node)
    workflow.add_node("publisher", publisher_node)

    # Define edges between nodes
    workflow.set_entry_point("collector")  # Entry point of the graph
    workflow.add_edge("collector", "filtering")
    workflow.add_edge("filtering", "planner")
    workflow.add_edge("planner", "writer")
    workflow.add_edge("writer", "translator")
    workflow.add_edge("translator", "publisher")
    workflow.add_edge("publisher", END)  # Exit point of the graph

    # Compile the graph into an executable application
    return workflow.compile()
