# agents/filtering_agent.py

from openai import OpenAI

from config.settings import settings
from core.logging import get_logger
from core.models import NewsItem

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the chief editor of a popular Telegram channel "AI News".
Your audience are tech-savvy enthusiasts, founders, early adopters, and developers.
They want to stay ahead of the curve, understand trends, and see cool new tech. They are NOT just boring academics.

Your task: pick ONE news item that is the most interesting, impactful, or "cool".

**CRITICAL FILTERS (MUST MATCH):**
1.  **Strictly AI:** The news MUST be about Artificial Intelligence, GenAI, LLMs, Robotics, or Data Science.
    *   REJECT generic tech news (crypto, phones, pure coding/security) if it has no AI angle.
2.  **No Boring Changelogs:** REJECT minor library updates (e.g., "fixed bug in v0.2") unless it's a major release of a famous tool.

**SELECTION CRITERIA (What we love):**
1.  **Major Releases:** New models (GPT, Claude, Gemini), new image generators, Sora-like video stuff.
2.  **Big Impact:** How AI changes business, science, or society.
3.  **"Wow" Factor:** Cool demos, unexpected use cases, agents doing crazy things.
4.  **Industry Moves:** Big investments, open-source vs closed-source wars, key strategic moves.

Here is the list of news:
{news_list}

**INSTRUCTIONS:**
- Analyze items against CRITICAL FILTERS.
- Return ONLY the INDEX number (e.g., "0", "1") of the best item.
- If NO item is good enough (all are off-topic or boring), return "-1".
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
