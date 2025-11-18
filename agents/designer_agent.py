# agents/designer_agent.py

import base64
import time
from io import BytesIO
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from PIL import Image

from config.settings import settings
from core.logging import get_logger
from core.models import NewsItem

logger = get_logger(__name__)

MIN_IMAGE_WIDTH = 600  # Minimum image width in pixels

# Prompts for vision model
IMAGE_ANALYSIS_PROMPT = """Analyze this image in the context of an AI news article.
Describe its content and relevance in a single, concise sentence.
- If it's a relevant photo, chart, or diagram, describe it.
- If it's an ad, UI screenshot, logo, or generic stock photo, state that.
Example: 'A photo of a server room with glowing racks, highly relevant.'
Example: 'A generic ad banner for a software product.'"""

IMAGE_SELECTION_PROMPT = """You are a photo editor for an AI news channel.
Your task is to select the single best image for a post.
The post text is:
---
{post_text}
---

Here are the available images with their descriptions:
{image_list}

Rules:
1. Choose the most visually compelling and contextually relevant image.
2. Strongly prefer real photos, diagrams, or charts over logos or UI screenshots.
3. AVOID ads and generic, irrelevant stock photos.
4. If no image is suitable, return the word "None".

Return ONLY the URL of the best image, or "None".
"""


def _get_image_urls_from_page(page_url: str) -> list[str]:
    """Scrapes a webpage to extract and clean image URLs."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }
    try:
        response = requests.get(page_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        urls = set()
        for img_tag in soup.find_all("img"):
            src = img_tag.get("src") or img_tag.get("data-src")
            if isinstance(src, (list, tuple)):
                src = src[0] if src else None

            if isinstance(src, str) and not src.startswith("data:"):
                full_url = urljoin(page_url, src)

                if "/_next/image" in full_url:
                    parsed_url = urlparse(full_url)
                    query_params = parse_qs(parsed_url.query)
                    if "url" in query_params:
                        clean_url = unquote(query_params["url"][0])
                        urls.add(clean_url)
                        logger.info("Cleaned proxy URL to: %s", clean_url)
                    continue

                urls.add(full_url)

        logger.info("Found %d unique image URLs on page.", len(urls))
        return list(urls)
    except requests.RequestException:
        logger.exception("Failed to fetch page for image scraping")
        return []


def _filter_images_by_size(image_urls: list[str]) -> list[dict]:
    """Download images, filters by size, and returns a list of dicts with URL and data."""
    valid_images = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }
    for url in image_urls:
        try:
            response = requests.get(url, headers=headers, stream=True, timeout=10)
            time.sleep(1)
            response.raise_for_status()

            image_data_bytes = response.raw.read(5 * 1024 * 1024)
            if not image_data_bytes:
                continue

            image_stream = BytesIO(image_data_bytes)
            with Image.open(image_stream) as img:
                width, _ = img.size
                if width >= MIN_IMAGE_WIDTH:
                    valid_images.append({"url": url, "data": image_data_bytes})
                    logger.info("Image %s meets width criteria (%dpx).", url, width)
        except Exception as e:
            logger.warning("Failed to process image %s: %s", url, e)
    return valid_images


def _describe_single_image(image_data: bytes, vision_client: OpenAI) -> str | None:
    """Describe a single image from its byte data."""
    try:
        base64_image = base64.b64encode(image_data).decode("utf-8")

        data_url = f"data:image/jpeg;base64,{base64_image}"

        logger.info("Analyzing image (from base64 data)...")
        response = vision_client.chat.completions.create(
            model=settings.VISION_MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_url}},
                        {"type": "text", "text": IMAGE_ANALYSIS_PROMPT},
                    ],
                },
            ],
            max_tokens=100,
            temperature=0.0,
        )
        desc = response.choices[0].message.content
        return desc.strip() if desc else None
    except Exception:
        logger.exception("Failed to analyze image during vision call")
        return None


def _describe_and_select_image(valid_images: list[dict], post_text: str) -> str | None:
    """Describe images using vision model and select the best one using LLM."""
    if not valid_images:
        return None

    vision_client = OpenAI(base_url=settings.VISION_API_URL, api_key=settings.OPENAI_API_KEY)
    text_client = OpenAI(base_url=settings.OPENAI_API_URL, api_key=settings.OPENAI_API_KEY)

    descriptions: list[dict[str, str]] = []
    for image_info in valid_images:
        desc = _describe_single_image(image_info["data"], vision_client)
        if desc:
            descriptions.append({"url": image_info["url"], "description": desc})

    if not descriptions:
        logger.warning("No images could be described.")
        return None

    image_list_str = "\n".join([f"- URL: {d['url']}\n  Description: {d['description']}" for d in descriptions])

    try:
        logger.info("Selecting the best image using LLM.")
        response = text_client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": IMAGE_SELECTION_PROMPT.format(post_text=post_text, image_list=image_list_str)}],
            max_tokens=500,
            temperature=0,
        )
        best_url = response.choices[0].message.content
        if best_url and best_url.strip().lower() != "none":
            logger.info("LLM selected image: %s", best_url.strip())
            return best_url.strip()
        logger.warning("LLM decided no image was suitable.")
        return None
    except Exception:
        logger.exception("LLM failed during image selection")
        return None


def find_image_for_post(news_item: NewsItem, post_text: str) -> str | None:
    """Search the article and select the best image for the post, with explicit logging."""
    logger.info("--- DESIGNER AGENT: Starting image search for article ---")

    all_urls = _get_image_urls_from_page(str(news_item.url))
    if not all_urls:
        logger.warning("--- DESIGNER AGENT FAILED: No image URLs found on the page. ---")
        return None

    valid_images = _filter_images_by_size(all_urls)
    if not valid_images:
        logger.warning(
            "--- DESIGNER AGENT FAILED: Found %d images, but none met the size requirement of %dpx. ---",
            len(all_urls),
            MIN_IMAGE_WIDTH,
        )
        return None

    best_image_url = _describe_and_select_image(valid_images, post_text)

    if best_image_url:
        logger.info("--- DESIGNER AGENT SUCCESS: Selected image: %s ---", best_image_url)
    else:
        logger.warning("--- DESIGNER AGENT FAILED: Images were analyzed, but none were selected as suitable by the LLM. ---")

    return best_image_url
