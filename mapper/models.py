"""Response schemas (pydantic) - FastAPI uses these for validation and the Swagger/OpenAPI docs."""
from typing import Optional

from pydantic import BaseModel, Field


class Component(BaseModel):
    component: str
    material: str
    weight_g: float = Field(ge=0)
    recyclable: bool
    supplier: Optional[str] = None


class Product(BaseModel):
    sku: str
    product_name: str
    country: str = Field(min_length=2, max_length=2)
    components: list[Component]
    total_packaging_weight_g: float


class RejectedRow(BaseModel):
    line: int
    reason: str
    raw: dict


class IngestResponse(BaseModel):
    client: str
    rows_received: int
    products: list[Product]
    rejected: list[RejectedRow]
