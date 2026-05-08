import os
import re
from typing import Optional
from supabase import create_client, Client
from loguru import logger


def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


def parse_price(price_str: Optional[str]) -> Optional[float]:
    """Extract numeric value from price string like '£34.99'."""
    if not price_str:
        return None
    match = re.search(r"[\d,]+\.?\d*", price_str.replace(",", ""))
    return float(match.group()) if match else None


def write_product(product: dict, search_query: str, scraped_by: Optional[str] = None) -> Optional[str]:
    """Insert a scraped product into Supabase. Returns the inserted row id."""
    client = get_client()

    row = {
        "search_query": search_query,
        "name": product.get("name", ""),
        "price": product.get("price"),
        "price_numeric": parse_price(product.get("price")),
        "image_url": product.get("image_url"),
        "product_url": product.get("product_url"),
        "source": product.get("source", ""),
        "ai_name": product.get("ai_name"),
        "ai_description": product.get("ai_desc"),
        "ai_category": product.get("ai_category"),
        "ai_colour": product.get("ai_colour"),
        "ai_material": product.get("ai_material"),
        "status": "pending",
        "scraped_by": scraped_by,
    }

    try:
        result = client.table("scraped_products").insert(row).execute()
        inserted = result.data[0] if result.data else None
        return inserted["id"] if inserted else None
    except Exception as e:
        logger.error(f"Failed to write product to Supabase: {e}")
        return None


def write_job_status(job_id: str, status: str, message: str, results_count: int = 0):
    """Upsert job status into scraper_jobs table."""
    client = get_client()
    try:
        client.table("scraper_jobs").upsert({
            "id": job_id,
            "status": status,
            "message": message,
            "results_count": results_count,
        }).execute()
    except Exception as e:
        logger.error(f"Failed to write job status: {e}")


def get_job_status(job_id: str) -> dict:
    client = get_client()
    try:
        result = client.table("scraper_jobs").select("*").eq("id", job_id).single().execute()
        return result.data or {}
    except Exception:
        return {}
