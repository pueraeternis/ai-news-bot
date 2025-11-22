# agents/filtering_agent.py

from openai import OpenAI

from config.settings import settings
from core.logging import get_logger
from core.models import NewsItem

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the chief editor of a popular Telegram channel "AI News", read by technical specialists.
Your task is to analyze the list of fresh news and pick ONE — the most important and interesting for your audience.

Selection criteria:
1. **Significance:** A major breakthrough, an important model release, or a notable event in the industry.
2. **Relevance for specialists:** Useful for developers, researchers, ML engineers.
3. **Specificity:** Avoid overly generic or purely marketing news.

Here is the list of news:
{news_list}

**INSTRUCTIONS:**
- Analyze these items.
- If you find a worthy news item, return ONLY its INDEX number (e.g., "0", "1").
- **CRITICAL:** If NONE of the news items are interesting, significant, or relevant enough, return "-1".
- Return only the number without any explanations.
"""
USER_PROMPT_TEMPLATE = "{news_list}"


def select_best_news_item(
    news_items: list[NewsItem],
    exclude_urls: list[str] | None = None,
) -> NewsItem | None:
    """
    Select the single best news item from a list.
    Return None if no item is selected or if LLM rejects all items.
    """
    if not news_items:
        logger.warning("News item list is empty, skipping selection.")
        return None

    candidate_items = news_items
    if exclude_urls:
        logger.info("Excluding %d URLs from selection.", len(exclude_urls))
        candidate_items = [item for item in news_items if str(item.url) not in exclude_urls]

    if not candidate_items:
        logger.warning("No candidate news items left after exclusion.")
        return None

    formatted_news = ""
    for i, item in enumerate(candidate_items):
        formatted_news += f"{i}. Title: {item.title}\n   Summary: {item.summary}\n\n"

    try:
        client = OpenAI(base_url=settings.OPENAI_API_URL, api_key=settings.OPENAI_API_KEY)
        user_prompt = USER_PROMPT_TEMPLATE.format(news_list=formatted_news)

        logger.info("Asking LLM to select the best news item from %d candidates.", len(candidate_items))

        response = client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=20,
        )

        response_content = response.choices[0].message.content
        if not response_content:
            logger.warning("LLM returned an empty response.")
            return None

        clean_content = response_content.strip()

        if clean_content == "-1":
            logger.info("LLM decided that NONE of the news items are worthy (returned -1).")
            return None

        selected_index = int(clean_content)

        if 0 <= selected_index < len(candidate_items):
            selected_item = candidate_items[selected_index]
            logger.info("LLM selected news item at index %d: '%s'", selected_index, selected_item.title)
            return selected_item

        logger.error("LLM returned an invalid index: %d", selected_index)
        return None

    except Exception:
        logger.exception("An unexpected error occurred during news selection.")
        return None
