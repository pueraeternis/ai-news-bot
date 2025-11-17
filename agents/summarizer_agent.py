# agents/summarizer_agent.py

from openai import OpenAI

from config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)

# Telegram's maximum caption length for photo posts
TELEGRAM_CAPTION_MAX_LENGTH = 800

SUMMARIZER_PROMPT = f"""You are an expert editor for a Telegram channel. Your task is to intelligently shorten the
following post to a maximum of {TELEGRAM_CAPTION_MAX_LENGTH} characters to be used as a photo caption.

**Crucial rules:**
1.  **Preserve the core message:** Do not lose the main idea or the key takeaways.
2.  **Keep the style:** Maintain the engaging and slightly informal tone.
3.  **MUST keep the source link:** The "Источник:" link at the end is mandatory and must be preserved exactly as is.
4.  **Be concise:** Remove filler words, merge sentences, and rephrase where necessary to meet the character limit.

Here is the text you need to shorten:
---
{{post_text}}
---

Return ONLY the shortened text.
"""


def summarize_for_caption(post_text: str) -> str:
    """Summarize a long post to fit into Telegram's 1024 character caption limit."""
    if len(post_text) <= TELEGRAM_CAPTION_MAX_LENGTH:
        return post_text

    logger.info("Post is too long for a caption (%d chars). Summarizing...", len(post_text))

    client = OpenAI(
        base_url=settings.OPENAI_API_URL,
        api_key=settings.OPENAI_API_KEY,
    )

    try:
        response = client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an expert editor specializing in concise text for social media."},
                {"role": "user", "content": SUMMARIZER_PROMPT.format(post_text=post_text)},
            ],
            temperature=0.5,
            max_tokens=TELEGRAM_CAPTION_MAX_LENGTH,
        )

        caption = response.choices[0].message.content
        if caption:
            logger.info("Successfully summarized post to %d chars.", len(caption))
            return caption.strip()

        logger.warning("Summarizer returned an empty response. Using truncated text as fallback.")
        return post_text[: TELEGRAM_CAPTION_MAX_LENGTH - 4] + "..."

    except Exception:
        logger.exception("Summarizer agent failed. Using truncated text as fallback.")
        return post_text[: TELEGRAM_CAPTION_MAX_LENGTH - 4] + "..."
