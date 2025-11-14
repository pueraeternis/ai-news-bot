# agents/filtering_agent.py


from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from config.settings import settings
from core.logging import get_logger
from core.models import NewsItem

logger = get_logger(__name__)

SELECTION_PROMPT = """
You are the chief editor of a popular Telegram channel "AI News", read by technical specialists.
Your task is to analyze the list of fresh news and pick ONE — the most important and interesting for your audience.

Selection criteria:
1. **Significance:** A major breakthrough, an important model release, or a notable event in the industry.
2. **Relevance for specialists:** Useful for developers, researchers, ML engineers.
3. **Specificity:** Avoid overly generic or purely marketing news.

Here is the list of news:
{news_list}

Analyze these items and return ONLY THE INDEX of the best news item.
For example, if the best item is the first one, return "0". If the second — "1", and so on.
Return only the number without any explanations.
"""


def select_best_news_item(news_items: list[NewsItem]) -> NewsItem | None:
    if not news_items:
        logger.warning("News item list is empty, skipping selection.")
        return None

    formatted_news = ""
    for i, item in enumerate(news_items):
        formatted_news += f"{i}. Title: {item.title}\n   Summary: {item.summary}\n\n"

    llm = ChatOpenAI(
        model=settings.LLM_MODEL_NAME,
        temperature=0,
        api_key=SecretStr(settings.OPENAI_API_KEY),
        base_url=settings.OPENAI_API_URL,
    )

    prompt = ChatPromptTemplate.from_template(SELECTION_PROMPT)
    parser = StrOutputParser()
    chain = prompt | llm | parser

    logger.info("Asking LLM to select the best news item from %d candidates.", len(news_items))

    try:
        response = chain.invoke({"news_list": formatted_news})
        selected_index = int(response.strip())

        if 0 <= selected_index < len(news_items):
            selected_item = news_items[selected_index]
            logger.info("LLM selected news item at index %d: '%s'", selected_index, selected_item.title)
            return selected_item
        logger.error("LLM returned an invalid index: %d", selected_index)
        return None

    except (ValueError, IndexError):
        logger.exception("Failed to parse LLM response or index out of bounds. Response: %s", response)
        return None
