from pydantic import BaseModel, HttpUrl


class Product(BaseModel):
    sku: str
    url: HttpUrl
    in_stock: bool
    name: str
    description: str
    price: float
