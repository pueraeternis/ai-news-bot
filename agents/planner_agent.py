# agents/planner_agent.py

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from config.settings import settings
from core.logging import get_logger
from core.models import NewsItem

logger = get_logger(__name__)

PLANNING_PROMPT = """
You are a content strategist for the "AI News" Telegram channel, which targets a technical audience of developers and ML engineers.
Your task is to create a structured plan for a post based on the provided news item.
The plan should be clear, concise, and easy for a writer to follow.

**IMPORTANT:** The provided summary may contain messy HTML tags. Ignore them and extract the core information.

**News Item to analyze:**
- **Title:** {title}
- **Summary:** {summary}

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


def create_post_plan(news_item: NewsItem | None) -> str | None:
    """Generate a structured plan for a blog post based on a single news item."""
    if not news_item:
        logger.warning("Planner agent received an empty news item.")
        return None

    llm = ChatOpenAI(
        model=settings.LLM_MODEL_NAME,
        temperature=0.7,  # Higher temperature for more creative titles/hooks
        api_key=SecretStr(settings.OPENAI_API_KEY),
        base_url=settings.OPENAI_API_URL,
    )
    prompt = ChatPromptTemplate.from_template(PLANNING_PROMPT)
    parser = StrOutputParser()
    chain = prompt | llm | parser

    logger.info("Generating post plan for news item: '%s'", news_item.title)

    try:
        plan = chain.invoke({"title": news_item.title, "summary": news_item.summary})
        logger.info("Successfully generated post plan.")
        return plan
    except Exception:
        logger.exception("Failed to generate post plan for news item: '%s'", news_item.title)
        return None
