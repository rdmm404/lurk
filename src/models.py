from pydantic import BaseModel, HttpUrl


class Product(BaseModel):
    sku: str
    url: HttpUrl
    in_stock: bool
    name: str
    description: str
    price: float


class ProductFilter(BaseModel):
    search: str
    min_price: int | None = None
    max_price: int | None = None
    in_stock: bool | None = None
    stores: list[str] | None = None
    zip_code: str | None = None
    region: str | None = None
    language: str | None = None
    categories: list[str] | None = None
