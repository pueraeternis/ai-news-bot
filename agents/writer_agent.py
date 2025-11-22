# agents/writer_agent.py

# agents/writer_agent.py

from openai import OpenAI

from config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)

WRITING_PROMPT_SYSTEM = """You are a top-tier tech blogger for the "AI News" Telegram channel.
Your audience: Tech enthusiasts, founders, devs, and early adopters.
Tone: Engaging, sharp, insightful, but NOT overly academic. Think "TechCrunch meets a smart Twitter thread".
Goal: Explain WHAT happened and WHY it matters in a way that makes people want to share it.

Format rules:
- Use Markdown (`**bold**` for emphasis).
- Be concise but punchy.
The final output should be ONLY the post text, ready for publication.
"""

WRITING_PROMPT_USER_TEMPLATE = """
Please write the final Telegram post based on this plan.

**Post Plan:**
{post_plan}
"""


def write_post_from_plan(post_plan: str | None) -> str | None:
    """Write a final, polished Telegram post based on a structured plan."""
    if not post_plan:
        logger.warning("Writer agent received an empty post plan.")
        return None

    client = OpenAI(
        base_url=settings.OPENAI_API_URL,
        api_key=settings.OPENAI_API_KEY,
    )

    user_prompt = WRITING_PROMPT_USER_TEMPLATE.format(
        post_plan=post_plan,
    )

    logger.info("Generating final post text from plan.")

    try:
        response = client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": WRITING_PROMPT_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

        final_post = response.choices[0].message.content
        if not final_post:
            logger.warning("LLM returned an empty post.")
            return None

        logger.info("Successfully generated final post text.")
        return final_post.strip()

    except Exception:
        logger.exception("Failed to generate final post from plan.")
        return None
