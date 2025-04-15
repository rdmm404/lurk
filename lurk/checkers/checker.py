from typing import Protocol
from lurk.models import Product
from lurk.http_client import HttpClient
from lurk.config import SearchFilters


class Checker(Protocol):
    def __init__(self, http_client: HttpClient): ...

    async def get_products(
        self, search: str, filters: SearchFilters | None = None
    ) -> list[Product]: ...
