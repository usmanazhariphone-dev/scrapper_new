import base64
import os
import json
from openai import OpenAI
from loguru import logger
from typing import Optional


class ImageAnalyser:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    async def analyse(self, image_path: str) -> dict:
        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            ext = image_path.rsplit(".", 1)[-1].lower()
            mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime};base64,{image_data}"},
                            },
                            {
                                "type": "text",
                                "text": (
                                    "Analyse this product image. Return ONLY a JSON object with these fields: "
                                    "name (short product name), description (1-2 sentences), "
                                    "category (e.g. shoes, clothing, accessories), "
                                    "colour (main colour), material (main material if visible). "
                                    "Example: {\"name\": \"Brown Leather Loafer\", \"description\": \"Classic brown leather loafer with rubber sole.\", "
                                    "\"category\": \"shoes\", \"colour\": \"brown\", \"material\": \"leather\"}"
                                ),
                            },
                        ],
                    }
                ],
                max_tokens=300,
            )

            text = response.choices[0].message.content.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)

        except Exception as e:
            logger.warning(f"ImageAnalyser failed for {image_path}: {e}")
            return {}
