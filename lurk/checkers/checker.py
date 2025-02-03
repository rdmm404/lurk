from typing import Protocol
from lurk.models import Product
from lurk.api_client import ApiClient
from lurk.config import CheckerConfig


class Checker(Protocol):
    def __init__(self, config: CheckerConfig, api_client: ApiClient): ...

    async def get_products(self) -> list[Product]: ...
