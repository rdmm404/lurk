"""
THIS IS A WIP
"""

from typing import Self, Any
from curl_cffi import requests
from rich import print

from lurk.checkers.checker import Checker
from lurk.models import Product
from lurk.config import CheckerConfig
from lurk.http_client import HttpClient


class CanadaComputersChecker(Checker):
    def __init__(self, http_client: HttpClient) -> None:
        self.http_client = http_client

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.http_client.close()

    async def get_products(self) -> list[Product]:
        resp = await self.http_client.get(
            "https://www.canadacomputers.com/en/search?s=4080",
        )
        with open("page.html", "w") as f:
            f.write(resp.text)
        print(resp.text)
        return []
