from typing import Protocol
from lurk.models import Product
from lurk.api_client import ApiClient
from lurk.config import SearchFilters


class Checker(Protocol):
    def __init__(self, api_client: ApiClient): ...

    async def get_products(
        self, search: str, filters: SearchFilters | None = None
    ) -> list[Product]: ...
