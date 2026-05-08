from pydantic import BaseModel
from typing import Optional


class SearchRequest(BaseModel):
    name: str
    image_base64: Optional[str] = None  # base64-encoded image for image-based search


class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # "running" | "done" | "failed"
    message: str
    results_count: int = 0


class ProductResult(BaseModel):
    id: Optional[str] = None
    search_query: str
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
    status: str = "pending"
    scraped_at: Optional[str] = None
