"""
Product Scraper API
Flow: image → OpenAI (extract name) → 8 adapters (scrape) → save to CRM product table
Run: uvicorn api:app --port 8000 (from scraper-service directory)
"""

import os
import sys
import base64
import random
import string
import re
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel
from typing import Optional, List

sys.path.insert(0, str(Path(__file__).parent))


# ── Request / Response models ────────────────────────────────────────────────

class SearchRequest(BaseModel):
    name: Optional[str] = None          # provide name directly
    image_base64: Optional[str] = None  # OR provide image — OpenAI extracts name


class ScrapedResult(BaseModel):
    name: str
    price: Optional[str] = None
    price_numeric: Optional[float] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    source: str
    ai_name: Optional[str] = None
    ai_description: Optional[str] = None
    ai_category: Optional[str] = None
    ai_colour: Optional[str] = None
    ai_material: Optional[str] = None


class SearchResponse(BaseModel):
    found: bool
    query: str
    results: List[ScrapedResult] = []
    saved_to_products: bool = False
    product_id: Optional[str] = None
    message: str = ""


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="CRM Product Scraper", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    """
    1. If image_base64 provided → send to OpenAI to extract product name
    2. Search all 8 retail sites with that name
    3. AI-analyse each product image
    4. Save all results to scraped_products table
    5. Save best result to product table
    """

    # ── Step 1: get product name ─────────────────────────────────────────────
    if req.image_base64:
        logger.info("[scraper] extracting product name from image via OpenAI...")
        product_name = await extract_name_from_image(req.image_base64)
        if not product_name:
            raise HTTPException(status_code=422, detail="Could not extract product name from image")
        logger.info(f"[scraper] OpenAI extracted name: '{product_name}'")
    elif req.name:
        product_name = req.name.strip()
    else:
        raise HTTPException(status_code=422, detail="Provide either 'name' or 'image_base64'")

    # ── Step 2: scrape all 8 sites ───────────────────────────────────────────
    logger.info(f"[scraper] searching '{product_name}' across 8 sites...")
    all_results: List[ScrapedResult] = []

    from scraper.core import ScraperCore
    from scraper.adapters import get_all_adapters
    from scraper.downloader import ImageDownloader
    from ai.analyser import ImageAnalyser

    async with ScraperCore() as core:
        adapters = get_all_adapters(core=core)
        analyser = ImageAnalyser()

        for adapter in adapters:
            try:
                logger.info(f"[scraper] → {adapter.SITE_NAME}")
                page = await core.new_page()
                products = await adapter.search_product(page, product_name)
                await page.close()

                for p in products:
                    ai = {}
                    if p.image_url:
                        downloader = ImageDownloader(adapter.SITE_NAME)
                        local_path = await downloader.download(p.image_url)
                        if local_path:
                            ai = await analyser.analyse(local_path)
                            try:
                                os.unlink(local_path)
                            except Exception:
                                pass

                    all_results.append(ScrapedResult(
                        name=p.name,
                        price=p.price,
                        price_numeric=parse_price(p.price),
                        image_url=p.image_url,
                        product_url=p.product_url,
                        source=adapter.SITE_NAME,
                        ai_name=ai.get("name"),
                        ai_description=ai.get("description"),
                        ai_category=ai.get("category"),
                        ai_colour=ai.get("colour"),
                        ai_material=ai.get("material"),
                    ))
                    logger.info(f"[scraper] ✓ {adapter.SITE_NAME}: {p.name}")

                if all_results:
                    logger.info(f"[scraper] product found on {adapter.SITE_NAME}, stopping search")
                    break

            except Exception as e:
                logger.warning(f"[scraper] {adapter.SITE_NAME} failed: {e}")
                continue

    if not all_results:
        logger.info(f"[scraper] no results found for '{product_name}'")
        return SearchResponse(found=False, query=product_name, message=f"No products found for '{product_name}' across all 8 sites")

    # ── Step 3: save all to scraped_products ─────────────────────────────────
    from supabase_writer import get_client
    client = get_client()

    for r in all_results:
        try:
            client.table("scraped_products").insert({
                "search_query": product_name,
                "name": r.name,
                "price": r.price,
                "price_numeric": r.price_numeric,
                "image_url": r.image_url,
                "product_url": r.product_url,
                "source": r.source,
                "ai_name": r.ai_name,
                "ai_description": r.ai_description,
                "ai_category": r.ai_category,
                "ai_colour": r.ai_colour,
                "ai_material": r.ai_material,
                "status": "pending",
            }).execute()
        except Exception as e:
            logger.error(f"[scraper] failed to save scraped_product: {e}")

    # ── Step 4: save best result to product table ─────────────────────────────
    best = all_results[0]
    product_id = None
    saved_to_products = False

    try:
        sku = "SCR-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        result = client.table("product").insert({
            "sku": sku,
            "name": best.ai_name or best.name,
            "base_price_cents": int((best.price_numeric or 0) * 100),
            "image_url": best.image_url,
            "category": best.ai_category,
            "description": best.ai_description,
            "status": "active",
        }).execute()
        if result.data:
            product_id = result.data[0]["id"]
            saved_to_products = True
            logger.info(f"[scraper] ✓ saved to product table: {best.ai_name or best.name} (id={product_id})")
    except Exception as e:
        logger.error(f"[scraper] failed to save to product table: {e}")

    return SearchResponse(
        found=True,
        query=product_name,
        results=all_results,
        saved_to_products=saved_to_products,
        product_id=product_id,
        message=f"Found {len(all_results)} results across {len(set(r.source for r in all_results))} sites. {'Saved to CRM.' if saved_to_products else 'Could not save to CRM.'}",
    )


# ── Helpers ──────────────────────────────────────────────────────────────────

async def extract_name_from_image(image_base64: str) -> Optional[str]:
    """Send image to OpenAI GPT-4o-mini and extract a clean product search name."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        # Detect mime type from base64 header or default to jpeg
        mime = "image/jpeg"
        if image_base64.startswith("data:"):
            mime = image_base64.split(";")[0].replace("data:", "")
            image_base64 = image_base64.split(",")[1]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{image_base64}"},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Look at this product image or product label. "
                            "Return ONLY a short product search name (3-6 words) suitable for searching on retail websites. "
                            "Examples: 'ladies tan clog slipper', 'mens black hoodie', 'white ceramic coffee mug'. "
                            "Return just the search phrase, nothing else."
                        ),
                    },
                ],
            }],
            max_tokens=50,
        )
        name = response.choices[0].message.content.strip().strip('"').strip("'")
        return name
    except Exception as e:
        logger.error(f"[openai] extract_name_from_image failed: {e}")
        return None


def parse_price(price_str: Optional[str]) -> Optional[float]:
    if not price_str:
        return None
    match = re.search(r"[\d,]+\.?\d*", price_str.replace(",", ""))
    return float(match.group()) if match else None
