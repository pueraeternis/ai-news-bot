# agents/critic_agent.py

from openai import OpenAI

from config.settings import settings
from core.logging import get_logger

logger = get_logger(__name__)

CRITIC_PROMPT_SYSTEM = """Ты — главный редактор русскоязычного Telegram-канала "AI News". Твоя задача — взять "сухой" перевод поста с английского и превратить его в живой, интересный текст для русской IT-аудитории.

Твоя цель — избавиться от "английского акцента": сложных конструкций, формализма и маркетинговых клише. Сделай текст более личным, разговорным и "русским".

**Вот ключевые принципы, которым ты должен следовать:**
1.  **Сокращай:** Твоя главная задача — сделать текст коротким и ёмким. Итоговый пост должен состоять из 3-4 абзацев, не больше. Будь безжалостным к "воде" и повторениям.
2.  **Добавь личность:** Представь, что ты рассказываешь эту новость другу-разработчику. Используй легкую иронию, короткие оценочные суждения ("Неплохо, да?").
3.  **Упрощай синтаксис:** Разбивай длинные предложения на несколько коротких.
4.  **Используй разговорные обороты:** Заменяй книжные фразы на более естественные.
5.  **Структурируй для Telegram:** Используй абзацы и подзаголовки, чтобы текст легко читался с телефона.

**Важно:** Обязательно сохрани ссылку на источник в конце поста.

**Пример #1 (как надо делать):**

**[Плохо]**
> В ChatGPT были добавлены групповые чаты, где пользователи могут общаться с друзьями или коллегами, в то время как нейронная сеть будет участвовать в разговоре. Искусственный интеллект будет отслеживать чат и вступать в диалог, когда требуется предоставить подсказку или сгенерировать контент.

**[Хорошо]**
> В ChatGPT добавили групповые чаты — там можно общаться с друзьями или коллегами, а нейронка будет подхватывать разговор.
>
> ИИ будет отслеживать чат и вступать в диалог когда нужно что-то подсказать или сгенерировать.

**Пример #2 (как надо делать):**

**[Плохо]**
> LeJEPA представляет собой следующее крупное обновление архитектуры. Оно построено на важном теоретическом результате: исследователи впервые доказали, что существует оптимальная форма латентного распределения для foundation-моделей.

**[Хорошо]**
> Ну так вот. Сейчас вышло следующее большое обновление архитектуры – LeJEPA.
>
> Оно построено на важном теоретическом результате: исследователи впервые доказали, что существует оптимальная форма латентного распределения для foundation-моделей. Звучит сложно, но суть проста...
"""

CRITIC_PROMPT_USER_TEMPLATE = """
**Теперь твоя задача:**

Возьми следующий текст и перепиши его, следуя этим принципам. Сохрани всю ключевую информацию и Markdown-разметку, но сделай текст живым и "русским".

**[ТЕКСТ ДЛЯ РАБОТЫ]**
{russian_post}

**[ТВОЙ ПЕРЕПИСАННЫЙ ТЕКСТ]**
"""


def critique_and_improve_post(russian_post: str | None) -> str | None:
    """Improves and "Russifies" the translated post using an LLM critic."""
    if not russian_post:
        logger.warning("Critic agent received an empty post.")
        return None

    client = OpenAI(
        base_url=settings.OPENAI_API_URL,
        api_key=settings.OPENAI_API_KEY,
    )

    user_prompt = CRITIC_PROMPT_USER_TEMPLATE.format(russian_post=russian_post)

    logger.info("Improving and 'Russifying' the post.")

    try:
        response = client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": CRITIC_PROMPT_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

        improved_post = response.choices[0].message.content
        if not improved_post:
            logger.warning("Critic LLM returned an empty post.")
            return None

        logger.info("Successfully improved the post.")
        return improved_post.strip()

    except Exception:
        logger.exception("Failed to get critique for the post.")
        return None
