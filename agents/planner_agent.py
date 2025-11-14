# agents/planner_agent.py

from openai import OpenAI

from config.settings import settings
from core.logging import get_logger
from core.models import NewsItem

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a content strategist for the "AI News" Telegram channel, which targets a technical audience of developers and ML engineers.
Your task is to create a structured plan for a post based on the provided news item.
The plan should be clear, concise, and easy for a writer to follow.

**IMPORTANT:** The provided summary may contain messy HTML tags. Ignore them and extract the core information.

**Your output must be a structured plan with the following sections:**

### Post Plan

- **Catchy Title:** [Create a compelling, short title for the Telegram post. It can be different from the original article title.]
- **Hook:** [Write a 1-2 sentence introduction that grabs the reader's attention and states the main news.]
- **Key Takeaways:**
    - [Create a bullet point summarizing the first key message.]
    - [Create a bullet point summarizing the second key message.]
    - [Create a bullet point summarizing the third key message.]
    - [Optional: Create a fourth bullet point if necessary.]
- **Conclusion:** [Write a concluding sentence that summarizes the importance of the news.]
- **Call to Action:** [Write a question to engage the audience, related to the news topic.]
"""

USER_PROMPT_TEMPLATE = """
**News Item to analyze:**
- **Title:** {title}
- **Summary:** {summary}
"""


def create_post_plan(news_item: NewsItem | None) -> str | None:
    if not news_item:
        logger.warning("Planner agent received an empty news item.")
        return None

    client = OpenAI(
        base_url=settings.OPENAI_API_URL,
        api_key=settings.OPENAI_API_KEY,
    )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        title=news_item.title,
        summary=news_item.summary,
    )

    logger.info("Generating post plan for news item: '%s'", news_item.title)

    try:
        response = client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

        plan = response.choices[0].message.content
        if not plan:
            logger.warning("LLM returned an empty plan.")
            return None

        logger.info("Successfully generated post plan.")
        return plan.strip()

    except Exception:
        logger.exception("Failed to generate post plan for news item: '%s'", news_item.title)
        return None
