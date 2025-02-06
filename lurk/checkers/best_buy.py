from typing import Any, TypedDict, no_type_check
from rich import print
from pydantic import ValidationError

from enum import StrEnum
from lurk.models import Product
from lurk.checkers.checker import Checker
from lurk.api_client import ApiClient
from lurk.config import SearchFilters


class BestBuyRoutes(StrEnum):
    SEARCH = "/api/v2/json/search"
    STOCK = "/ecomm-api/availability/products"


class BestBuySearchParams(TypedDict, total=False):
    currentRegion: str
    lang: str
    query: str
    sortBy: str
    sortDir: str
    path: str
    include: str


BestBuyProductsParams = TypedDict(
    "BestBuyProductsParams",
    {
        "accept": str,
        "accept-language": str,
        "locations": str,
        "postalCode": str,
        "skus": str,
    },
    total=False,
)


class BestBuyChecker(Checker):
    base_url = "https://www.bestbuy.ca"

    def __init__(self, api_client: ApiClient) -> None:
        self.client = api_client.set_base_url(self.base_url)

    async def get_products(
        self, search: str, filters: SearchFilters | None = None
    ) -> list[Product]:
        if not filters:
            filters = SearchFilters()
        products: list[Product] = []
        raw_products = await self._search_products(search, filters)

        for p in raw_products:
            try:
                product = self._parse_product(p)  # type: ignore
            except ValidationError as e:
                print(f"Couldn't parse product {p}. Error: {e}")
                continue

            products.append(product)

        stocks = await self._fetch_products([p.sku for p in products], filters)

        for product in products:
            availability = stocks.get(product.sku)
            if not availability:
                print(f"availability not found for product {product.sku}")
                continue
            pickup_available = availability.get("pickup", {}).get("purchasable", False)
            shipping_available = availability.get("shipping", {}).get(
                "purchasable", False
            )
            product.in_stock = pickup_available or shipping_available

        return products

    async def _search_products(
        self, search: str, filters: SearchFilters
    ) -> list[dict[str, Any]]:
        default_search_params: BestBuySearchParams = {
            "lang": "en-CA",
            "sortBy": "relevance",
            "sortDir": "desc",
            "include": "facets, redirects",
            # "currentRegion": "ON",
            # "isPLP": True,
            # "categoryId": "",
            # "page": 1,
            # "pageSize": 24,
            # "hasConsent": True,
            # "contextId": "",
            # "token": "0704351726c71900c5ce6c67cc0100004b1f1c00il0vtu4thkhi8jh",
        }
        filter_params: BestBuySearchParams = {"query": search}

        filter_params["path"] = ""

        if filters.categories:
            filter_params["path"] += (
                ";".join(f"category:{c}" for c in filters.categories) + ";"
            )
        if filters.min_price or filters.max_price:
            price_range_str = f"currentPrice:[{filters.min_price or '*'} TO {filters.max_price or '*'}]"
            filter_params["path"] += price_range_str

        filter_params["path"] = filter_params["path"].rstrip(";")

        search_resp = await self.client.get(
            BestBuyRoutes.SEARCH, params=default_search_params | filter_params
        )
        products: list[dict[str, Any]] = search_resp.json.get("products", [])
        return products

    @no_type_check
    def _parse_product(self, raw_product: dict[str, Any]) -> Product:
        return Product(
            sku=raw_product.get("sku"),
            url=self.base_url + raw_product.get("productUrl"),
            in_stock=False,
            name=raw_product.get("name"),
            description=raw_product.get("shortDescription"),
            price=raw_product.get("salePrice"),
        )

    async def _fetch_products(
        self, skus: list[str], filters: SearchFilters
    ) -> dict[str, dict[str, Any]]:
        if not skus:
            return {}
        default_params: BestBuyProductsParams = {
            "accept": "application/vnd.bestbuy.simpleproduct.v1+json",
            "accept-language": "en-CA",
        }
        params: BestBuyProductsParams = {"skus": "|".join(skus)}
        if filters.stores:
            params["locations"] = "|".join(filters.stores)
        if filters.zip_code:
            params["postalCode"] = filters.zip_code

        resp = await self.client.get(
            BestBuyRoutes.STOCK, params=default_params | params
        )
        stocks = resp.json.get("availabilities", [])
        stocks_mapping: dict[str, dict[str, Any]] = {}
        for s in stocks:
            if not (sku := s.get("sku")):
                continue
            stocks_mapping[sku] = s
        return stocks_mapping
