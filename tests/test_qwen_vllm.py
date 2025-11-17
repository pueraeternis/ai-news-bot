import json
import logging
from typing import Any

import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "http://localhost:19000/v1/chat/completions"
MODEL_NAME = "Qwen/Qwen3-VL-30B-A3B-Instruct"
IMAGE_URL = "https://www.newhorizons.com/Portals/2/EasyDNNnews/1012/what-happens-if-ai-replaces-humans.jpg"


def describe_image(image_url: str) -> str | None:
    """Send multimodal request to model and get image description."""
    payload: dict[str, Any] = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": "Describe this image in detail."},
                ],
            },
        ],
        "max_tokens": 512,
        "temperature": 0.0,
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()

        result: dict[str, Any] = response.json()
        description: str = result["choices"][0]["message"]["content"]
        logger.info("--- Image Description ---")
        logger.info("%s", description)
        logger.info("------------------------")
        return description

    except requests.exceptions.RequestException:
        if "response" in locals() and response.text:
            logger.exception("Request failed. Server response: %s", response.text)
        else:
            logger.exception("Request failed")
        return None


if __name__ == "__main__":
    describe_image(IMAGE_URL)
