# agents/translator_agent.py

from openai import OpenAI

from config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)

TRANSLATION_PROMPT_SYSTEM = """You are a professional technical translator specializing in content for IT specialists.
Your task is to translate a post for the "AI News" Telegram channel from English to Russian.

**Crucial requirements:**
1.  **Audience:** The target audience is Russian-speaking developers, ML engineers, and data scientists. The translation must be accurate, use appropriate technical terminology, and sound natural in Russian.
2.  **Style:** Maintain the original's engaging, slightly informal tone. Avoid overly academic or dry language.
3.  **Formatting:** You MUST preserve all original Markdown formatting (`**bold text**`, `*italic text*`), all emojis (like 🚀, 💡, 👇), and all line breaks exactly as they are in the original text. This is critical for the post's structure in Telegram.

Return ONLY the translated Russian text. Do not add any extra comments or explanations.
"""

TRANSLATION_PROMPT_USER_TEMPLATE = """
Please translate the following post to Russian while following all the rules in the system prompt:

---
{english_post}
---
"""


def translate_post_to_russian(english_post: str | None) -> str | None:
    """Translate a finished post from English to Russian using an LLM."""
    if not english_post:
        logger.warning("Translator agent received an empty post.")
        return None

    client = OpenAI(
        base_url=settings.OPENAI_API_URL,
        api_key=settings.OPENAI_API_KEY,
    )

    user_prompt = TRANSLATION_PROMPT_USER_TEMPLATE.format(english_post=english_post)

    logger.info("Translating final post to Russian.")

    try:
        response = client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": TRANSLATION_PROMPT_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

        translated_post = response.choices[0].message.content
        if not translated_post:
            logger.warning("LLM returned an empty translation.")
            return None

        logger.info("Successfully translated the post.")
        return translated_post.strip()

    except Exception:
        logger.exception("Failed to translate the post.")
        return None
