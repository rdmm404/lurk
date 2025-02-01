from typing import Protocol, Self, Any
from lurk.models import Product, ProductFilter


class Checker(Protocol):
    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, *_: Any) -> None: ...

    async def get_products(self, filter: ProductFilter) -> list[Product]: ...
