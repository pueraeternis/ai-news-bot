# agents/summarizer_agent.py

from openai import OpenAI

from config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)


SUMMARIZER_PROMPT_TEMPLATE = """You are a text processing API. Your only function is to shorten the user's text to fit a strict character limit.

**CRITICAL RULE:** The returned text MUST NOT exceed **{char_limit}** characters. This is a hard technical constraint. Failure to comply will result in system error.

**Instructions:**
1.  Analyze the provided text.
2.  Rewrite it to be as concise as possible while preserving the main idea, key points, and style.
3.  You MUST preserve the "Источник:" link at the end of the text.
4.  Your entire output, including the source link and any formatting, must be less than **{char_limit}** characters.

**TEXT TO PROCESS:**
---
{post_text}
---

Return ONLY the shortened text. Do not add any commentary or apologies.
"""


def summarize_for_caption(post_text: str, max_tokens: int) -> str:
    """Summarize a long post to fit into Telegram's caption character limit."""
    char_limit = int(max_tokens * 2.2)

    logger.info(
        "Post is too long for a caption (%d chars). Summarizing with max_tokens=%d (target chars: ~%d)...",
        len(post_text),
        max_tokens,
        char_limit,
    )

    client = OpenAI(base_url=settings.OPENAI_API_URL, api_key=settings.OPENAI_API_KEY)

    prompt = SUMMARIZER_PROMPT_TEMPLATE.format(post_text=post_text, char_limit=char_limit)

    try:
        response = client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a text processing API that strictly follows length constraints."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=max_tokens,
        )

        caption = response.choices[0].message.content
        if caption:
            logger.info("Successfully summarized post to %d chars.", len(caption))
            return caption.strip()

        logger.warning("Summarizer returned an empty response. Returning original text.")
        return post_text

    except Exception:
        logger.exception("Summarizer agent failed. Returning original text.")
        return post_text
