from pydantic import BaseModel
from typing import Optional


class ProductResult(BaseModel):
    name: str
    price: Optional[str] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
