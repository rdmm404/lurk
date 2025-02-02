from typing import Self, Any
from curl_cffi import requests
from rich import print

from lurk.checkers.checker import Checker
from lurk.models import Product, ProductFilter
from lurk.config import Config

class CanadaComputersChecker(Checker):
    def __init__(self, config: Config) -> None:
        self.session = requests.AsyncSession()
        self._config = config

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.session.close()

    async def get_products(self, filter: ProductFilter) -> list[Product]:
        resp = await self.session.get(
            "https://www.canadacomputers.com/en/search?s=4080",
            headers=self._config.client.headers,
        )
        with open("page.html", "w") as f:
            f.write(resp.text)
        print(resp.text)
        return []
