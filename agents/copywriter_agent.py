# agents/copywriter_agent.py

from openai import OpenAI

from config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)

COPYWRITER_PROMPT_SYSTEM = """Ты — профессиональный технический журналист, пишущий лонгриды для Хабра, VC.ru и Tproger.
Твоя аудитория: IT-специалисты, инженеры, аналитики данных и технические директора.

**Твоя задача:**
Написать глубокую, структурированную статью (лонгрид) на основе предоставленного материала.

**Требования к формату:**
1.  **Формат:** Markdown. Используй заголовки уровней # (H1) для названия, ## (H2) и ### (H3) для структуры.
2.  **Стиль:** Экспертный, аналитический, но читаемый. Без "воды", но с деталями.
3.  **Структура статьи:**
    *   **Кликбейтный, но честный заголовок (H1).**
    *   **Лид (Вступление):** Краткая суть новости и почему это важно для индустрии.
    *   **Основная часть:** Разбор технологии, примеры использования, сравнение с аналогами.
    *   **Аналитика:** Что это значит для рынка? Какие перспективы?
    *   **Заключение:** Краткий итог.

**Важно:** Текст должен быть объемным и подробным, готовым к публикации на профильных ресурсах.
"""

COPYWRITER_PROMPT_USER_TEMPLATE = """
Вот исходный материал (перевод новости):
---
{russian_text}
---

Напиши на его основе полноценную статью в формате Markdown.
"""


def write_long_read_article(russian_text: str | None) -> str | None:
    """
    Expand the translated text into a full Markdown article (Long Read).
    """
    if not russian_text:
        logger.warning("Copywriter agent received empty text.")
        return None

    client = OpenAI(
        base_url=settings.OPENAI_API_URL,
        api_key=settings.OPENAI_API_KEY,
    )

    user_prompt = COPYWRITER_PROMPT_USER_TEMPLATE.format(russian_text=russian_text)

    logger.info("Copywriter Agent: Writing long-read article.")

    try:
        response = client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": COPYWRITER_PROMPT_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

        article = response.choices[0].message.content
        if not article:
            logger.warning("Copywriter Agent returned an empty article.")
            return None

        logger.info("Copywriter Agent successfully wrote the article.")
        return article.strip()

    except Exception:
        logger.exception("Failed to write long-read article.")
        return None
